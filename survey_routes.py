# ── ADD THESE IMPORTS at top of main.py ──────────────────────
# from models import Assessment, Response, Report, SurveyForm, SurveyQuestion

# ── ADD THESE PYDANTIC MODELS ─────────────────────────────────

class SurveyFormCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SurveyFormUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SurveyQuestionCreate(BaseModel):
    question_text: str
    dimension: str
    question_type: str = "scale"
    order_index: int = 0

class SurveyQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    dimension: Optional[str] = None
    question_type: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class QuestionsReorder(BaseModel):
    question_ids: list  # ordered list of question IDs

# ── SURVEY FORM ROUTES ────────────────────────────────────────

@app.get("/survey-editor")
def survey_editor_page(request: Request):
    if not verify_wp_token(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="survey_editor.html",
        context={"skip_auth": True, "wp_token": os.environ.get('DASHBOARD_SECRET_TOKEN')}
    )

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
        "is_active": f.is_active, "created_at": f.created_at,
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
        # Deactivate all other forms first
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

# ── QUESTION ROUTES ───────────────────────────────────────────

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
        "form_id": form.id,
        "form_name": form.name,
        "is_active": form.is_active,
        "questions": [{
            "id": q.id, "question_text": q.question_text,
            "dimension": q.dimension, "question_type": q.question_type,
            "order_index": q.order_index, "is_active": q.is_active
        } for q in form.questions]
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

    # Get max order index
    max_order = db.query(SurveyQuestion).filter(
        SurveyQuestion.form_id == form_id
    ).count()

    question = SurveyQuestion(
        form_id=form_id,
        question_text=data.question_text,
        dimension=data.dimension,
        question_type=data.question_type,
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
