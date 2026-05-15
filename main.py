from models import Assessment, Response, Report, SurveyForm, SurveyQuestion
from fastapi.templating import Jinja2Templates
from fastapi import Request, FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from database import engine, get_db, Base
from models import Assessment, Response, Report
from questions import QUESTIONS, DIMENSIONS, OPEN_TEXT_QUESTIONS, DEMOGRAPHICS, ANSWER_LABELS
from scoring import calculate_scores
from auth import verify_password, create_access_token, verify_token, PHOEBE_USERNAME, PHOEBE_PASSWORD
from gemini_report import generate_report
from email_service import send_report_to_all
import uuid
import os

app = FastAPI()
Base.metadata.create_all(bind=engine)

# ── Auto-migrate new columns ──────────────────────────────────
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE assessments ADD COLUMN IF NOT EXISTS survey_form_id VARCHAR"))
        conn.commit()
except Exception as e:
    print(f"Migration note: {e}")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WordPress Token Auth ──────────────────────────────────────
def verify_wp_token(request: Request):
    WP_SECRET_TOKEN = os.environ.get('DASHBOARD_SECRET_TOKEN')
    token = request.query_params.get('token') or request.headers.get('X-WP-Token')
    return bool(token and token == WP_SECRET_TOKEN)

# ── Pydantic Models ───────────────────────────────────────────
class AssessmentCreate(BaseModel):
    client_name: str
    client_email: str
    org_name: str
    industry: Optional[str] = None

class AssessmentUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    org_name: Optional[str] = None
    industry: Optional[str] = None

class SubmitAssessment(BaseModel):
    token: str
    demographics: dict
    answers: dict
    open_text: dict

class LoginData(BaseModel):
    username: str
    password: str

# ── Public Routes ─────────────────────────────────────────────

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

@app.get("/assess/{token}")
def assessment_page(token: str, request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"token": token})

@app.get("/assessment/{token}")
def get_assessment(token: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == token).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Assessment link has expired")
    if assessment.status == "completed":
        assessment.status = "pending"
    db.commit()
    return {"client_name": assessment.client_name, "org_name": assessment.org_name, "status": assessment.status}

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
    return {"token": token, "link": f"{base_url}/assess/{token}", "message": "Assessment created successfully"}

@app.post("/assessment/submit")
def submit_assessment(data: SubmitAssessment, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == data.token).first()
    if not assessment:
        assessment = Assessment(
            token=data.token, client_name="Test Client", client_email="test@test.com",
            org_name="Test Organisation", expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    for q in QUESTIONS:
        db.add(Response(
            assessment_id=assessment.id, question_id=q["id"],
            dimension=q["dimension"], answer=data.answers.get(str(q["id"]), 3),
        ))

    responses = [{"question_id": q["id"], "dimension": q["dimension"], "answer": data.answers.get(str(q["id"]), 3)} for q in QUESTIONS]
    result = calculate_scores(responses)

    # Generate Gemini report
    ai_narrative = ""
    try:
        ai_narrative = generate_report(
            client_name=assessment.client_name, org_name=assessment.org_name,
            industry=assessment.industry or "Not specified",
            overall_score=result["overall_score"], maturity_stage=result["maturity_stage"],
            risk_band=result["risk_band"], dimension_scores=result["dimension_scores"],
            top_risks=result["top_risks"],
        )
        print("✅ Gemini report generated")
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        ai_narrative = "Report generation failed. Please contact support."

    db.add(Report(
        assessment_id=assessment.id, overall_score=result["overall_score"],
        maturity_stage=result["maturity_stage"], risk_band=result["risk_band"],
        narrative=ai_narrative,
    ))
    assessment.status = "completed"
    db.commit()

    # Send emails
    try:
        send_report_to_all(
            client_name=assessment.client_name, client_email=assessment.client_email,
            org_name=assessment.org_name, overall_score=result["overall_score"],
            maturity_stage=result["maturity_stage"], risk_band=result["risk_band"],
            report_text=ai_narrative,
        )
    except Exception as e:
        print(f"❌ Email failed: {e}")

    return {
        "message": "Assessment submitted successfully",
        "overall_score": result["overall_score"], "maturity_stage": result["maturity_stage"],
        "risk_band": result["risk_band"], "top_risks": result["top_risks"],
        "dimension_scores": result["dimension_scores"],
    }

@app.get("/report/{token}")
def get_report(token: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.token == token).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not assessment.report:
        raise HTTPException(status_code=404, detail="Report not ready yet")
    return {"org_name": assessment.org_name, "overall_score": assessment.report.overall_score,
            "maturity_stage": assessment.report.maturity_stage, "risk_band": assessment.report.risk_band}

# ── Auth ──────────────────────────────────────────────────────


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/auth/login")
def login(data: LoginData):
    if data.username != PHOEBE_USERNAME or not verify_password(data.password, PHOEBE_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_access_token({"sub": data.username})}

# ── Dashboard ─────────────────────────────────────────────────

@app.get("/dashboard")
def dashboard_page(request: Request):
    if not verify_wp_token(request):
        return RedirectResponse(url="/login", status_code=302)
    wp_token = os.environ.get('DASHBOARD_SECRET_TOKEN')
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"skip_auth": True, "wp_token": wp_token}
    )

@app.get("/dashboard/assessments")
def get_assessments(
    request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")

    assessments = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
    return {"assessments": [{
        "assessment_id": a.id, "client_name": a.client_name, "client_email": a.client_email,
        "org_name": a.org_name, "industry": a.industry, "status": a.status,
        "created_at": a.created_at,
        "overall_score": a.report.overall_score if a.report else None,
        "maturity_stage": a.report.maturity_stage if a.report else None,
    } for a in assessments]}

@app.get("/dashboard/report/{assessment_id}")
def get_report_narrative(
    assessment_id: str, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment or not assessment.report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "client_name": assessment.client_name, "org_name": assessment.org_name,
        "overall_score": assessment.report.overall_score, "maturity_stage": assessment.report.maturity_stage,
        "risk_band": assessment.report.risk_band, "narrative": assessment.report.narrative,
        "created_at": assessment.report.created_at,
    }

@app.put("/dashboard/assessment/{assessment_id}")
def update_assessment(
    assessment_id: str, data: AssessmentUpdate, request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if data.client_name: assessment.client_name = data.client_name
    if data.client_email: assessment.client_email = data.client_email
    if data.org_name: assessment.org_name = data.org_name
    if data.industry: assessment.industry = data.industry
    db.commit()
    return {"message": "Assessment updated successfully"}

@app.delete("/dashboard/assessment/{assessment_id}")
def delete_assessment(
    assessment_id: str, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")

    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    db.query(Response).filter(Response.assessment_id == assessment_id).delete()
    db.query(Report).filter(Report.assessment_id == assessment_id).delete()
    db.delete(assessment)
    db.commit()
    return {"message": "Assessment deleted successfully"}

# ── Admin Debug ───────────────────────────────────────────────

@app.get("/admin/assessments")
def get_all_assessments(db: Session = Depends(get_db)):
    assessments = db.query(Assessment).all()
    return {"count": len(assessments), "assessments": [
        {"id": a.id, "token": a.token, "client_name": a.client_name,
         "client_email": a.client_email, "org_name": a.org_name,
         "status": a.status, "created_at": a.created_at}
        for a in assessments
    ]}

@app.get("/admin/reports")
def get_all_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).all()
    return {"count": len(reports), "reports": [
        {"id": r.id, "assessment_id": r.assessment_id,
         "overall_score": r.overall_score, "maturity_stage": r.maturity_stage, "risk_band": r.risk_band}
        for r in reports
    ]}

@app.get("/admin/responses")
def get_all_responses(db: Session = Depends(get_db)):
    responses = db.query(Response).all()
    return {"count": len(responses), "responses": [
        {"id": r.id, "assessment_id": r.assessment_id,
         "question_id": r.question_id, "dimension": r.dimension, "answer": r.answer}
        for r in responses
    ]}
