from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import base_url
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from database import engine, get_db, Base
from models import Assessment, Response, Report
from questions import QUESTIONS, DIMENSIONS, OPEN_TEXT_QUESTIONS, DEMOGRAPHICS, ANSWER_LABELS
from scoring import calculate_scores
import uuid

Base.metadata.create_all(bind=engine, checkfirst=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ───────────────────────────────────────────
class AssessmentCreate(BaseModel):
    client_name: str
    client_email: str
    org_name: str
    industry: Optional[str] = None

class SubmitAssessment(BaseModel):
    token: str
    demographics: dict
    answers: dict
    open_text: dict

# ── Routes ───────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "CereViva NeuroSafety API is running"}

@app.get("/questions")
def get_questions():
    return {
        "questions": QUESTIONS,
        "dimensions": DIMENSIONS,
        "answer_labels": ANSWER_LABELS,
        "open_text_questions": OPEN_TEXT_QUESTIONS,
        "demographics": DEMOGRAPHICS,
    }

@app.post("/assessment/create")
def create_assessment(data: AssessmentCreate, db: Session = Depends(get_db)):
    token = str(uuid.uuid4())
    assessment = Assessment(
        token=token,
        client_name=data.client_name,
        client_email=data.client_email,
        org_name=data.org_name,
        industry=data.industry,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    base_url = os.environ.get("BASE_URL", "http://localhost:3000")
    return {
        "token": token,
        "link": f"{base_url}/assess/{token}",
        "message": "Assessment created successfully",
    }

@app.get("/assessment/{token}")
def get_assessment(token: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == token).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Assessment link has expired")
    if assessment.status == "completed":
        raise HTTPException(status_code=400, detail="Assessment already completed")
    return {
        "client_name": assessment.client_name,
        "org_name": assessment.org_name,
        "status": assessment.status,
    }

@app.post("/assessment/submit")
def submit_assessment(data: SubmitAssessment, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == data.token).first()
    if not assessment:
    # For testing - create a temporary assessment if token not found
        assessment = Assessment(
        token=data.token,
        client_name="Test Client",
        client_email="test@test.com",
        org_name="Test Organisation",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Save responses
    for q in QUESTIONS:
        answer_value = data.answers.get(str(q["id"]), 3)
        response = Response(
            assessment_id=assessment.id,
            question_id=q["id"],
            dimension=q["dimension"],
            answer=answer_value,
        )
        db.add(response)

    # Build responses list for scoring
    responses = [
        {
            "question_id": q["id"],
            "dimension": q["dimension"],
            "answer": data.answers.get(str(q["id"]), 3),
        }
        for q in QUESTIONS
    ]

    # Run scoring engine
    result = calculate_scores(responses)

    # Save report
    report = Report(
        assessment_id=assessment.id,
        overall_score=result["overall_score"],
        maturity_stage=result["maturity_stage"],
        risk_band=result["risk_band"],
        narrative="",
    )
    db.add(report)

    # Mark assessment as completed
    assessment.status = "completed"
    db.commit()

    return {
        "message": "Assessment submitted successfully",
        "overall_score": result["overall_score"],
        "maturity_stage": result["maturity_stage"],
        "risk_band": result["risk_band"],
        "top_risks": result["top_risks"],
        "dimension_scores": result["dimension_scores"],
    }

@app.get("/report/{token}")
def get_report(token: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == token).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not assessment.report:
        raise HTTPException(status_code=404, detail="Report not ready yet")
    return {
        "org_name": assessment.org_name,
        "overall_score": assessment.report.overall_score,
        "maturity_stage": assessment.report.maturity_stage,
        "risk_band": assessment.report.risk_band,
    }

@app.get("/assess/{token}")
def assessment_page(token: str, request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "token": token})

# ── Admin / Debug Routes ──────────────────────────────────────

@app.get("/admin/assessments")
def get_all_assessments(db: Session = Depends(get_db)):
    assessments = db.query(Assessment).all()
    return {
        "count": len(assessments),
        "assessments": [
            {
                "id": a.id,
                "token": a.token,
                "client_name": a.client_name,
                "client_email": a.client_email,
                "org_name": a.org_name,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in assessments
        ],
    }

@app.get("/admin/reports")
def get_all_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).all()
    return {
        "count": len(reports),
        "reports": [
            {
                "id": r.id,
                "assessment_id": r.assessment_id,
                "overall_score": r.overall_score,
                "maturity_stage": r.maturity_stage,
                "risk_band": r.risk_band,
            }
            for r in reports
        ],
    }

@app.get("/admin/responses")
def get_all_responses(db: Session = Depends(get_db)):
    responses = db.query(Response).all()
    return {
        "count": len(responses),
        "responses": [
            {
                "id": r.id,
                "assessment_id": r.assessment_id,
                "question_id": r.question_id,
                "dimension": r.dimension,
                "answer": r.answer,
            }
            for r in responses
        ],
    }
