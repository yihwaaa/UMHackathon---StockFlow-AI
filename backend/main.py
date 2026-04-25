import json
import os
from typing import Tuple

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_engine.glm_client import GLM_MODEL, analyze_discrepancy_with_glm
from . import models, schemas
from .database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="StockFlow AI API", version="1.1")

REQUIRED_FIELDS = ("supplier", "invoice_no", "product", "expected_qty", "actual_qty")


@app.get("/api/v1/health")
def health_check():
    glm_configured = bool(os.getenv("GLM_API_KEY", "").strip())
    return {
        "status": "ok",
        "service": "stockflow-api",
        "glm_model": GLM_MODEL,
        "glm_configured": glm_configured,
        "ai_mode": "glm+deterministic" if glm_configured else "deterministic_fallback",
    }


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _split_missing_fields(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _compute_required_missing_fields(case: models.Case) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = getattr(case, field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def _resolve_issue_type(value: str | None) -> schemas.IssueType:
    try:
        return schemas.IssueType(value or schemas.IssueType.UNKNOWN.value)
    except ValueError:
        return schemas.IssueType.UNKNOWN


def _log_case_event(db: Session, case_id: int, event_type: str, message: str, actor: str = "system") -> None:
    db.add(
        models.CaseEvent(
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            message=message,
        )
    )


def _find_open_duplicate_case(
    db: Session,
    supplier: str | None,
    invoice_no: str | None,
    product: str | None = None,
    exclude_case_id: int | None = None,
) -> models.Case | None:
    normalized_invoice = _normalize_text(invoice_no)
    if not normalized_invoice:
        return None

    query = db.query(models.Case).filter(
        func.lower(func.coalesce(models.Case.invoice_no, "")) == normalized_invoice,
        models.Case.status != schemas.CaseStatus.RESOLVED.value,
    )

    normalized_supplier = _normalize_text(supplier)
    if normalized_supplier:
        query = query.filter(func.lower(func.coalesce(models.Case.supplier, "")) == normalized_supplier)

    normalized_product = _normalize_text(product)
    if normalized_product:
        query = query.filter(func.lower(func.coalesce(models.Case.product, "")) == normalized_product)

    if exclude_case_id is not None:
        query = query.filter(models.Case.id != exclude_case_id)

    return query.order_by(models.Case.id.desc()).first()


def _classify_case(total_expected: float, total_actual: float, notes: str) -> Tuple[schemas.IssueType, str]:
    normalized_notes = (notes or "").lower()
    if "duplicate" in normalized_notes or "double bill" in normalized_notes:
        return schemas.IssueType.DUPLICATE_BILLING, "MEDIUM"

    if total_actual < total_expected:
        delta = total_expected - total_actual
        if delta >= 10 or (total_expected > 0 and (delta / total_expected) >= 0.2):
            return schemas.IssueType.STOCK_SHORTAGE, "HIGH"
        return schemas.IssueType.STOCK_SHORTAGE, "MEDIUM"

    if total_actual > total_expected:
        delta = total_actual - total_expected
        if delta >= 10:
            return schemas.IssueType.OVER_DELIVERY, "MEDIUM"
        return schemas.IssueType.OVER_DELIVERY, "LOW"

    return schemas.IssueType.INVOICE_MISMATCH, "LOW"


def _recommend_action(issue_type: schemas.IssueType, urgency: str, missing_fields: list[str]) -> str:
    if missing_fields:
        return "Collect Missing Information"
    if issue_type == schemas.IssueType.STOCK_SHORTAGE and urgency == "HIGH":
        return "Manager Review"
    if issue_type in {schemas.IssueType.DUPLICATE_BILLING, schemas.IssueType.INVOICE_MISMATCH}:
        return "Finance Review"
    if issue_type == schemas.IssueType.OVER_DELIVERY:
        return "Inventory Reconciliation"
    return "Operations Review"


@app.get("/api/v1/cases", response_model=list[schemas.CaseDBBase])
def get_cases(db: Session = Depends(get_db)):
    return db.query(models.Case).order_by(models.Case.id.desc()).all()


@app.get("/api/v1/cases/{case_id}/events", response_model=list[schemas.CaseEventRead])
def get_case_events(case_id: int, db: Session = Depends(get_db)):
    case_exists = db.query(models.Case.id).filter(models.Case.id == case_id).first()
    if case_exists is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return (
        db.query(models.CaseEvent)
        .filter(models.CaseEvent.case_id == case_id)
        .order_by(models.CaseEvent.id.desc())
        .all()
    )


@app.patch("/api/v1/cases/{case_id}/status")
def update_case_status(case_id: int, request: schemas.CaseStatusUpdate, db: Session = Depends(get_db)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    previous_status = case.status
    case.status = request.status.value
    _log_case_event(
        db,
        case.id,
        "STATUS_UPDATED",
        f"Status changed from {previous_status} to {case.status}.",
        actor="operator",
    )
    db.commit()
    db.refresh(case)

    return {"case_id": case.id, "status": case.status, "message": "Status updated"}


@app.patch("/api/v1/cases/{case_id}/clarify")
def clarify_case(case_id: int, request: schemas.CaseClarifyRequest, db: Session = Depends(get_db)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    updated_fields: list[str] = []
    if request.supplier is not None:
        case.supplier = request.supplier.strip() or None
        updated_fields.append("supplier")
    if request.invoice_no is not None:
        case.invoice_no = request.invoice_no.strip() or None
        updated_fields.append("invoice_no")
    if request.product is not None:
        case.product = request.product.strip() or None
        updated_fields.append("product")
    if request.expected_qty is not None:
        case.expected_qty = request.expected_qty
        updated_fields.append("expected_qty")
    if request.actual_qty is not None:
        case.actual_qty = request.actual_qty
        updated_fields.append("actual_qty")
    if request.notes is not None:
        case.discrepancy_details = request.notes.strip() or None
        updated_fields.append("notes")

    previous_status = case.status
    missing_fields = _compute_required_missing_fields(case)
    case.missing_fields = ",".join(missing_fields)

    issue_type = _resolve_issue_type(case.issue_type)
    urgency = case.urgency or "LOW"
    if case.expected_qty is not None and case.actual_qty is not None:
        issue_type, urgency = _classify_case(case.expected_qty, case.actual_qty, case.discrepancy_details or "")

    case.issue_type = issue_type.value
    case.urgency = urgency
    case.next_action = _recommend_action(issue_type, urgency, missing_fields)
    case.status = schemas.CaseStatus.PENDING_INFO.value if missing_fields else schemas.CaseStatus.ROUTED.value

    update_message = "Clarification submitted."
    if updated_fields:
        update_message = f"Clarification updated fields: {', '.join(updated_fields)}."
    if previous_status != case.status:
        update_message += f" Status changed from {previous_status} to {case.status}."

    _log_case_event(db, case.id, "CASE_CLARIFIED", update_message, actor="operator")
    db.commit()
    db.refresh(case)

    return {
        "case_id": case.id,
        "status": case.status,
        "issue_type": case.issue_type,
        "urgency": case.urgency,
        "next_action": case.next_action,
        "missing_fields": _split_missing_fields(case.missing_fields),
        "message": "Case clarification saved",
    }


@app.post("/api/v1/cases/manual")
def create_manual_case(request: schemas.ManualCaseCreate, db: Session = Depends(get_db)):
    total_expected = sum(item.expected_qty for item in request.line_items)
    total_actual = sum(item.actual_qty for item in request.line_items)
    line_items_payload = [item.model_dump() for item in request.line_items]

    primary_product = (
        request.line_items[0].product
        if len(request.line_items) == 1
        else f"MULTI_ITEM ({len(request.line_items)} lines)"
    )

    duplicate_case = _find_open_duplicate_case(
        db,
        supplier=request.supplier,
        invoice_no=request.invoice_no,
        product=request.line_items[0].product if len(request.line_items) == 1 else None,
    )
    if duplicate_case and not request.force_create:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Potential duplicate detected (open case #{duplicate_case.id}).",
                "existing_case_id": duplicate_case.id,
                "action": "Set force_create=true to create a new case anyway.",
            },
        )

    issue_type, urgency = _classify_case(total_expected, total_actual, request.notes or "")
    missing_fields: list[str] = []
    next_action = _recommend_action(issue_type, urgency, missing_fields)
    status = schemas.CaseStatus.ROUTED

    synthesized_input = (
        f"Supplier {request.supplier}; Invoice {request.invoice_no}; "
        f"Expected {total_expected}; Actual {total_actual}; "
        f"Products {', '.join([item.product for item in request.line_items])}."
    )

    discrepancy_blob = {
        "notes": request.notes,
        "line_items": line_items_payload,
    }

    ai_output = schemas.AIAnalysisResponse(
        issue_type=issue_type,
        urgency=urgency,
        entities=schemas.ExtractedEntities(
            supplier=request.supplier,
            store=request.store,
            invoice_no=request.invoice_no,
            product=primary_product,
            expected_qty=total_expected,
            actual_qty=total_actual,
            discrepancy_details=request.notes,
        ),
        workflow=schemas.WorkflowRecommendation(
            next_action=next_action,
            missing_fields=missing_fields,
        ),
    )

    db_case = models.Case(
        raw_input=synthesized_input,
        status=status.value,
        issue_type=ai_output.issue_type.value,
        urgency=ai_output.urgency,
        supplier=ai_output.entities.supplier,
        store=ai_output.entities.store,
        invoice_no=ai_output.entities.invoice_no,
        product=ai_output.entities.product,
        expected_qty=ai_output.entities.expected_qty,
        actual_qty=ai_output.entities.actual_qty,
        discrepancy_details=json.dumps(discrepancy_blob, ensure_ascii=True),
        next_action=ai_output.workflow.next_action,
        missing_fields=",".join(ai_output.workflow.missing_fields),
    )

    db.add(db_case)
    db.flush()
    _log_case_event(db, db_case.id, "CASE_CREATED", "Case created from structured table intake.")
    if duplicate_case and request.force_create:
        _log_case_event(
            db,
            db_case.id,
            "DUPLICATE_OVERRIDE",
            f"Force-created despite existing open case #{duplicate_case.id}.",
            actor="operator",
        )
    db.commit()
    db.refresh(db_case)

    return {
        "case_id": db_case.id,
        "mode": "manual_table",
        "ai_analysis": ai_output,
        "db_status": "saved",
    }


@app.post("/api/v1/analyze")
def analyze_and_create_case(request: schemas.CaseCreate, db: Session = Depends(get_db)):
    try:
        ai_output = analyze_discrepancy_with_glm(request.raw_input)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {exc}")

    duplicate_case = _find_open_duplicate_case(
        db,
        supplier=ai_output.entities.supplier,
        invoice_no=ai_output.entities.invoice_no,
        product=ai_output.entities.product,
    )
    if duplicate_case and not request.force_create:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Potential duplicate detected (open case #{duplicate_case.id}).",
                "existing_case_id": duplicate_case.id,
                "action": "Set force_create=true to create a new case anyway.",
            },
        )

    status = schemas.CaseStatus.ROUTED
    if len(ai_output.workflow.missing_fields) > 0:
        status = schemas.CaseStatus.PENDING_INFO

    db_case = models.Case(
        raw_input=request.raw_input,
        status=status.value,
        issue_type=ai_output.issue_type.value,
        urgency=ai_output.urgency,
        supplier=ai_output.entities.supplier,
        store=ai_output.entities.store,
        invoice_no=ai_output.entities.invoice_no,
        product=ai_output.entities.product,
        expected_qty=ai_output.entities.expected_qty,
        actual_qty=ai_output.entities.actual_qty,
        discrepancy_details=ai_output.entities.discrepancy_details,
        next_action=ai_output.workflow.next_action,
        missing_fields=",".join(ai_output.workflow.missing_fields),
    )

    db.add(db_case)
    db.flush()
    _log_case_event(db, db_case.id, "CASE_CREATED", "Case created from AI text intake.")
    if ai_output.workflow.missing_fields:
        _log_case_event(
            db,
            db_case.id,
            "MISSING_FIELDS_DETECTED",
            f"Missing fields detected: {', '.join(ai_output.workflow.missing_fields)}.",
        )
    if duplicate_case and request.force_create:
        _log_case_event(
            db,
            db_case.id,
            "DUPLICATE_OVERRIDE",
            f"Force-created despite existing open case #{duplicate_case.id}.",
            actor="operator",
        )
    db.commit()
    db.refresh(db_case)

    return {"case_id": db_case.id, "mode": "ai_text", "ai_analysis": ai_output, "db_status": "saved"}
