from models import Assessment, Response, Report, SurveyForm, SurveyQuestion
from typing import Optional
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

from schemas import SurveyFormCreate, SurveyFormUpdate, SurveyQuestionCreate, SurveyQuestionUpdate, QuestionsReorder

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

class QuestionsReorder(BaseModel):
    question_ids: list

class PublicSubmitAssessment(BaseModel):
    client_name: str
    client_email: str
    org_name: str
    industry: Optional[str] = None
    demographics: dict
    answers: dict
    open_text: dict
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
    # Always allow reuse — reset to pending each visit
    assessment.status = "pending"
    db.commit()
    return {
        "client_name": assessment.client_name,
        "org_name": assessment.org_name,
        "status": assessment.status,
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
        expires_at=datetime.utcnow() + timedelta(days=365),
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
        raise HTTPException(status_code=404, detail="Assessment not found")

    #  Delete old responses so new ones can be saved fresh
    db.query(Response).filter(Response.assessment_id == assessment.id).delete()
    db.query(Report).filter(Report.assessment_id == assessment.id).delete()
    db.commit()

    for q in QUESTIONS:
        answer_value = data.answers.get(str(q["id"]), 3)
        response = Response(
            assessment_id=assessment.id,
            question_id=q["id"],
            dimension=q["dimension"],
            answer=answer_value,
        )
        db.add(response)

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
        print("Gemini report generated")
    except Exception as e:
        print(f"Gemini failed: {e}")
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
        print(f" Email failed: {e}")

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

@app.post("/dashboard/survey-forms/{form_id}/questions/reorder")
def reorder_questions(form_id: str, data: QuestionsReorder, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    for idx, qid in enumerate(data.question_ids):
        db.query(SurveyQuestion).filter(SurveyQuestion.id == qid).update({"order_index": idx})
    db.commit()
    return {"message": "Reordered"}

@app.get("/survey-editor")
def survey_editor_page(request: Request):
    if not verify_wp_token(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="survey_editor.html",
        context={
            "skip_auth": True,
            "wp_token": os.environ.get('DASHBOARD_SECRET_TOKEN')
        }
    )

# ── SURVEY FORM ROUTES ────────────────────────────────────────

@app.get("/dashboard/survey-forms")
def get_survey_forms(
    request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    forms = db.query(SurveyForm).order_by(SurveyForm.created_at.desc()).all()
    return {"forms": [{
        "id": f.id, "name": f.name, "description": f.description,
        "is_active": f.is_active, "created_at": str(f.created_at),
        "question_count": len([q for q in f.questions if q.is_active])
    } for f in forms]}

@app.post("/dashboard/survey-forms")
def create_survey_form(
    data: SurveyFormCreate, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    form = SurveyForm(name=data.name, description=data.description, is_active=False)
    db.add(form)
    db.commit()
    db.refresh(form)
    return {"id": form.id, "name": form.name, "message": "Form created successfully"}

@app.put("/dashboard/survey-forms/{form_id}")
def update_survey_form(
    form_id: str, data: SurveyFormUpdate, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    form = db.query(SurveyForm).filter(SurveyForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if data.name: form.name = data.name
    if data.description is not None: form.description = data.description
    if data.is_active is not None:
        if data.is_active:
            db.query(SurveyForm).update({"is_active": False})
        form.is_active = data.is_active
    db.commit()
    return {"message": "Form updated successfully"}

@app.delete("/dashboard/survey-forms/{form_id}")
def delete_survey_form(
    form_id: str, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    form = db.query(SurveyForm).filter(SurveyForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.is_active:
        raise HTTPException(status_code=400, detail="Cannot delete active form")
    db.delete(form)
    db.commit()
    return {"message": "Form deleted successfully"}

@app.get("/dashboard/survey-forms/{form_id}/questions")
def get_form_questions(
    form_id: str, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    form = db.query(SurveyForm).filter(SurveyForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    return {
        "form_id": form.id, "form_name": form.name, "is_active": form.is_active,
        "questions": [{
            "id": q.id, "question_text": q.question_text, "dimension": q.dimension,
            "question_type": q.question_type, "order_index": q.order_index, "is_active": q.is_active
        } for q in sorted(form.questions, key=lambda x: x.order_index)]
    }

@app.post("/dashboard/survey-forms/{form_id}/questions")
def add_question(
    form_id: str, data: SurveyQuestionCreate, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    form = db.query(SurveyForm).filter(SurveyForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    max_order = db.query(SurveyQuestion).filter(SurveyQuestion.form_id == form_id).count()

    q_text = data.question_text or data.text
    q_type = data.question_type or data.type or "scale"

    if not q_text:
        raise HTTPException(status_code=422, detail="question_text is required")
    question = SurveyQuestion(
    form_id=form_id,
    question_text=q_text,
    dimension=data.dimension,
    question_type=q_type,
    order_index=max_order,
    is_active=True,
)
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"id": question.id, "message": "Question added successfully"}

@app.put("/dashboard/questions/{question_id}")
def update_question(
    question_id: str, data: SurveyQuestionUpdate, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    question = db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if data.question_text is not None: question.question_text = data.question_text
    if data.dimension is not None: question.dimension = data.dimension
    if data.question_type is not None: question.question_type = data.question_type
    if data.order_index is not None: question.order_index = data.order_index
    if data.is_active is not None: question.is_active = data.is_active
    db.commit()
    return {"message": "Question updated successfully"}

@app.delete("/dashboard/questions/{question_id}")
def delete_question(
    question_id: str, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    question = db.query(SurveyQuestion).filter(SurveyQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return {"message": "Question deleted successfully"}

@app.post("/dashboard/survey-forms/{form_id}/questions/reorder")
def reorder_questions(
    form_id: str, data: QuestionsReorder, request: Request, db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
):
    if not verify_wp_token(request) and not (credentials and verify_token(credentials.credentials)):
        raise HTTPException(status_code=401, detail="Unauthorized")
    for idx, qid in enumerate(data.question_ids):
        db.query(SurveyQuestion).filter(SurveyQuestion.id == qid).update({"order_index": idx})
    db.commit()
    return {"message": "Reordered successfully"}

# ── SURVEY PYDANTIC MODELS ────────────────────────────────────

class SurveyFormCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SurveyFormUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None



class SurveyQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    dimension: Optional[str] = None
    question_type: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class QuestionsReorder(BaseModel):
    question_ids: list

@app.get("/survey")
def public_survey_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.post("/assessment/submit-public")
def submit_public_assessment(data: PublicSubmitAssessment, db: Session = Depends(get_db)):
    assessment = Assessment(
        token=str(uuid.uuid4()),
        client_name=data.client_name,
        client_email=data.client_email,
        org_name=data.org_name,
        industry=data.industry,
        expires_at=datetime.utcnow() + timedelta(days=3650),
        status="completed",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    for q in QUESTIONS:
        answer_value = data.answers.get(str(q["id"]), 3)
        db.add(Response(
            assessment_id=assessment.id,
            question_id=q["id"],
            dimension=q["dimension"],
            answer=answer_value,
        ))

    responses = [{"question_id": q["id"], "dimension": q["dimension"], "answer": data.answers.get(str(q["id"]), 3)} for q in QUESTIONS]
    result = calculate_scores(responses)

    ai_narrative = ""
    try:
        ai_narrative = generate_report(
            client_name=data.client_name, org_name=data.org_name,
            industry=data.industry or "Not specified",
            overall_score=result["overall_score"], maturity_stage=result["maturity_stage"],
            risk_band=result["risk_band"], dimension_scores=result["dimension_scores"],
            top_risks=result["top_risks"],
        )
    except Exception as e:
        print(f"Gemini failed: {e}")
        ai_narrative = "Report generation failed. Please contact support."

    db.add(Report(
        assessment_id=assessment.id,
        overall_score=result["overall_score"],
        maturity_stage=result["maturity_stage"],
        risk_band=result["risk_band"],
        narrative=ai_narrative,
    ))
    db.commit()

    try:
        send_report_to_all(
            client_name=data.client_name, client_email=data.client_email,
            org_name=data.org_name, overall_score=result["overall_score"],
            maturity_stage=result["maturity_stage"], risk_band=result["risk_band"],
            report_text=ai_narrative,
        )
    except Exception as e:
        print(f" Email failed: {e}")

    return {
        "message": "Assessment submitted successfully",
        "overall_score": result["overall_score"],
        "maturity_stage": result["maturity_stage"],
        "risk_band": result["risk_band"],
        "top_risks": result["top_risks"],
        "dimension_scores": result["dimension_scores"],
    }