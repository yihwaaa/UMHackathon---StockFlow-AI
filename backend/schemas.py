from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

class CaseStatus(str, Enum):
    NEW = "NEW"
    PENDING_INFO = "PENDING_INFO"
    ROUTED = "ROUTED"
    RESOLVED = "RESOLVED"

class IssueType(str, Enum):
    STOCK_SHORTAGE = "STOCK_SHORTAGE"
    INVOICE_MISMATCH = "INVOICE_MISMATCH"
    OVER_DELIVERY = "OVER_DELIVERY"
    DUPLICATE_BILLING = "DUPLICATE_BILLING"
    UNKNOWN = "UNKNOWN"

class ExtractedEntities(BaseModel):
    supplier: Optional[str] = Field(None, description="Name of the supplier")
    store: Optional[str] = Field(None, description="Name or ID of the store")
    invoice_no: Optional[str] = Field(None, description="Invoice number")
    product: Optional[str] = Field(None, description="Product name or SKU")
    expected_qty: Optional[float] = Field(None, description="Quantity expected based on invoice")
    actual_qty: Optional[float] = Field(None, description="Quantity actually received")
    discrepancy_details: Optional[str] = Field(None, description="Other notes about the discrepancy")

class WorkflowRecommendation(BaseModel):
    next_action: str = Field(..., description="Recommended next step, e.g. 'Manager Review', 'Finance Review'")
    missing_fields: List[str] = Field(default=[], description="List of required fields missing from the input")

class AIAnalysisResponse(BaseModel):
    issue_type: IssueType
    urgency: str = Field(..., description="HIGH, MEDIUM, or LOW")
    entities: ExtractedEntities
    workflow: WorkflowRecommendation

class CaseCreate(BaseModel):
    raw_input: str = Field(..., min_length=10, max_length=5000)
    force_create: bool = False


class ManualLineItem(BaseModel):
    product: str = Field(..., min_length=2, max_length=120)
    sku: Optional[str] = Field(None, max_length=64)
    expected_qty: float = Field(..., ge=0)
    actual_qty: float = Field(..., ge=0)


class ManualCaseCreate(BaseModel):
    supplier: str = Field(..., min_length=2, max_length=120)
    invoice_no: str = Field(..., min_length=2, max_length=64)
    store: Optional[str] = Field(None, max_length=120)
    line_items: List[ManualLineItem] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=2000)
    force_create: bool = False


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class CaseClarifyRequest(BaseModel):
    supplier: Optional[str] = Field(None, min_length=2, max_length=120)
    invoice_no: Optional[str] = Field(None, min_length=2, max_length=64)
    product: Optional[str] = Field(None, min_length=2, max_length=120)
    expected_qty: Optional[float] = Field(None, ge=0)
    actual_qty: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class CaseDBBase(BaseModel):
    id: int
    status: CaseStatus
    issue_type: str
    urgency: Optional[str]
    supplier: Optional[str]
    store: Optional[str]
    product: Optional[str]
    invoice_no: Optional[str]
    expected_qty: Optional[float]
    actual_qty: Optional[float]
    discrepancy_details: Optional[str]
    next_action: Optional[str]
    missing_fields: Optional[str]
    raw_input: str

    class Config:
        from_attributes = True


class CaseEventRead(BaseModel):
    id: int
    case_id: int
    event_type: str
    actor: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
