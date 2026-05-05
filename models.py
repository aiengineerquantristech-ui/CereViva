from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, nullable=False)
    client_name = Column(String, nullable=False)
    client_email = Column(String, nullable=False)
    org_name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    responses = relationship("Response", back_populates="assessment")
    report = relationship("Report", back_populates="assessment", uselist=False)


class Response(Base):
    __tablename__ = "responses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, nullable=False)
    dimension = Column(String, nullable=False)
    answer = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="responses")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    maturity_stage = Column(String, nullable=False)
    risk_band = Column(String, nullable=False)
    narrative = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="report")