from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
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
    survey_form_id = Column(String, ForeignKey("survey_forms.id"), nullable=True)

    responses = relationship("Response", back_populates="assessment")
    report = relationship("Report", back_populates="assessment", uselist=False)
    survey_form = relationship("SurveyForm", back_populates="assessments")


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


# ── Survey Form Tables ────────────────────────────────────────

class SurveyForm(Base):
    __tablename__ = "survey_forms"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("SurveyQuestion", back_populates="form", cascade="all, delete-orphan", order_by="SurveyQuestion.order_index")
    assessments = relationship("Assessment", back_populates="survey_form")


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id = Column(String, ForeignKey("survey_forms.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    dimension = Column(String, nullable=False)
    question_type = Column(String, default="scale")  # scale, open_text, demographic
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    form = relationship("SurveyForm", back_populates="questions")
