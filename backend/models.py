from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from .database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, index=True, default="NEW")
    
    # Raw input from user
    raw_input = Column(Text)
    
    # AI Classification
    issue_type = Column(String, default="UNKNOWN")
    urgency = Column(String, default="LOW")
    
    # Extracted Entities
    supplier = Column(String, nullable=True)
    store = Column(String, nullable=True)
    invoice_no = Column(String, nullable=True)
    product = Column(String, nullable=True)
    expected_qty = Column(Float, nullable=True)
    actual_qty = Column(Float, nullable=True)
    discrepancy_details = Column(Text, nullable=True)
    
    # Workflow
    next_action = Column(String, nullable=True)
    missing_fields = Column(String, nullable=True) # Stored as comma-separated string


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True, nullable=False)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False, default="system")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
