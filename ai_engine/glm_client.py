import json
import os
import re

import requests

from backend.schemas import AIAnalysisResponse, ExtractedEntities, IssueType, WorkflowRecommendation

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = os.getenv("GLM_MODEL", "ilmu-glm-5.1")


def _extract_invoice_no(text: str):
    patterns = [
        r"(?i)invoice\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z]{1,6}[-_/]?[A-Z0-9]{2,20})",
        r"(?i)\b(inv[-_/]?[A-Z0-9]{2,20})\b",
        r"(?i)#\s*([A-Z]{1,6}[-_/]?[A-Z0-9]{2,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_supplier(text: str):
    patterns = [
        r"(?i)supplier\s*[:\-]?\s*([A-Za-z0-9&()'.,\-\s]{2,60})",
        r"(?i)from\s+([A-Za-z0-9&()'.,\-\s]{2,60})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip(" .,")
            value = re.split(r"(?i)\b(delivered|invoice|sent|shipped|received|we|and)\b", value)[0].strip(" .,")
            if value:
                return value
    return None


def _extract_product(text: str):
    patterns = [
        r"(?i)\b(?:boxes|box|units|pcs|pieces|cartons|packs|bottles|kg|kgs|liters|items)\s+of\s+([A-Za-z0-9\-\s]{2,60})",
        r"(?i)product\s*[:\-]?\s*([A-Za-z0-9\-\s]{2,60})",
        r"(?i)sku\s*[:\-]?\s*([A-Za-z0-9\-]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip(" .,")
            value = re.split(r"(?i)\b(invoice|expected|actual|short|missing|delivered|received)\b", value)[0].strip(" .,")
            if value:
                return value
    return None


def _extract_quantities(text: str):
    expected = None
    actual = None

    expected_match = re.search(r"(?i)(?:invoice\s*(?:says|shows|states)?|expected)\s*[:\-]?\s*(\d+(?:\.\d+)?)", text)
    actual_match = re.search(r"(?i)(?:actual|received|delivered)\s*[:\-]?\s*(\d+(?:\.\d+)?)", text)
    short_match = re.search(r"(?i)(?:short|shortage|missing)\s*(?:by)?\s*(\d+(?:\.\d+)?)", text)

    if expected_match:
        expected = float(expected_match.group(1))
    if actual_match:
        actual = float(actual_match.group(1))

    if expected is None and actual is not None and short_match:
        expected = actual + float(short_match.group(1))
    if actual is None and expected is not None and short_match:
        actual = expected - float(short_match.group(1))

    return expected, actual


def _deterministic_extract(raw_text: str) -> ExtractedEntities:
    expected_qty, actual_qty = _extract_quantities(raw_text)
    return ExtractedEntities(
        supplier=_extract_supplier(raw_text),
        store=None,
        invoice_no=_extract_invoice_no(raw_text),
        product=_extract_product(raw_text),
        expected_qty=expected_qty,
        actual_qty=actual_qty,
        discrepancy_details=None,
    )


def _compute_missing_fields(entities: ExtractedEntities):
    required = ["supplier", "invoice_no", "product", "expected_qty", "actual_qty"]
    missing = []
    for field in required:
        value = getattr(entities, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def _normalize_next_action(issue_type: IssueType, urgency: str, missing_fields: list[str]):
    if missing_fields:
        return "Collect Missing Information"
    if issue_type in {IssueType.STOCK_SHORTAGE, IssueType.DUPLICATE_BILLING} and urgency == "HIGH":
        return "Manager Review"
    if issue_type == IssueType.INVOICE_MISMATCH:
        return "Finance Review"
    return "Operations Review"


def _fallback_response(raw_text: str) -> AIAnalysisResponse:
    entities = _deterministic_extract(raw_text)
    missing_fields = _compute_missing_fields(entities)
    issue_type = IssueType.INVOICE_MISMATCH
    urgency = "MEDIUM"

    if entities.expected_qty is not None and entities.actual_qty is not None:
        if entities.actual_qty < entities.expected_qty:
            issue_type = IssueType.STOCK_SHORTAGE
            urgency = "HIGH" if (entities.expected_qty - entities.actual_qty) >= 5 else "MEDIUM"
        elif entities.actual_qty > entities.expected_qty:
            issue_type = IssueType.OVER_DELIVERY
            urgency = "LOW"

    return AIAnalysisResponse(
        issue_type=issue_type,
        urgency=urgency,
        entities=entities,
        workflow=WorkflowRecommendation(
            next_action=_normalize_next_action(issue_type, urgency, missing_fields),
            missing_fields=missing_fields,
        ),
    )


def analyze_discrepancy_with_glm(raw_text: str):
    """Call GLM for structured extraction and merge with deterministic parsers for precision."""
    api_key = os.getenv("GLM_API_KEY", "").strip()
    system_prompt = """
You are an AI Store Operations Copilot for retail discrepancy workflows.

Your output must be ONLY a single valid JSON object, no markdown and no extra text.

Rules:
1) Never invent invoice numbers, products, or quantities.
2) If not found in input, return null.
3) Quantities must be numbers.
4) issue_type must be one of: STOCK_SHORTAGE, INVOICE_MISMATCH, OVER_DELIVERY, DUPLICATE_BILLING, UNKNOWN.
5) urgency must be one of: HIGH, MEDIUM, LOW.

Output schema:
{
  "issue_type": "STOCK_SHORTAGE",
  "urgency": "HIGH",
  "entities": {
    "supplier": null,
    "store": null,
    "invoice_no": null,
    "product": null,
    "expected_qty": null,
    "actual_qty": null,
    "discrepancy_details": null
  },
  "workflow": {
    "next_action": "Manager Review",
    "missing_fields": []
  }
}
"""

    if not api_key:
        return _fallback_response(raw_text)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text},
        ],
        "temperature": 0.0,
    }

    try:
        response = requests.post(GLM_API_URL, headers=headers, json=payload, timeout=35)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]["content"]
        cleaned = message.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        llm_output = AIAnalysisResponse(**data)

        deterministic = _deterministic_extract(raw_text)
        merged_entities = ExtractedEntities(
            supplier=llm_output.entities.supplier or deterministic.supplier,
            store=llm_output.entities.store or deterministic.store,
            invoice_no=llm_output.entities.invoice_no or deterministic.invoice_no,
            product=llm_output.entities.product or deterministic.product,
            expected_qty=llm_output.entities.expected_qty if llm_output.entities.expected_qty is not None else deterministic.expected_qty,
            actual_qty=llm_output.entities.actual_qty if llm_output.entities.actual_qty is not None else deterministic.actual_qty,
            discrepancy_details=llm_output.entities.discrepancy_details,
        )

        missing_fields = _compute_missing_fields(merged_entities)
        next_action = _normalize_next_action(llm_output.issue_type, llm_output.urgency, missing_fields)

        return AIAnalysisResponse(
            issue_type=llm_output.issue_type,
            urgency=llm_output.urgency,
            entities=merged_entities,
            workflow=WorkflowRecommendation(
                next_action=next_action,
                missing_fields=missing_fields,
            ),
        )
    except Exception:
        return _fallback_response(raw_text)
