"""
Run this ONCE to migrate questions from questions.py into the database.
Command: python migrate_questions.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, get_db, Base, SessionLocal
from models import SurveyForm, SurveyQuestion
from questions import QUESTIONS, OPEN_TEXT_QUESTIONS, DEMOGRAPHICS

def migrate():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already migrated
        existing = db.query(SurveyForm).filter(SurveyForm.name == "CereViva NeuroSafety Assessment").first()
        if existing:
            print("✅ Already migrated! Form exists in database.")
            print(f"   Form ID: {existing.id}")
            print(f"   Active: {existing.is_active}")
            return

        print("🔄 Starting migration...")

        # Create the default form
        form = SurveyForm(
            name="CereViva NeuroSafety Assessment",
            description="A comprehensive workplace neuroscience and psychological safety assessment covering 10 dimensions.",
            is_active=True,
        )
        db.add(form)
        db.flush()

        # Add scale questions
        for i, q in enumerate(QUESTIONS):
            question = SurveyQuestion(
                form_id=form.id,
                question_text=q["text"],
                dimension=q["dimension"],
                question_type="scale",
                order_index=i,
                is_active=True,
            )
            db.add(question)

        # Add open text questions
        offset = len(QUESTIONS)
        for i, q_text in enumerate(OPEN_TEXT_QUESTIONS):
            question = SurveyQuestion(
                form_id=form.id,
                question_text=q_text,
                dimension="Open Text",
                question_type="open_text",
                order_index=offset + i,
                is_active=True,
            )
            db.add(question)

        db.commit()
        print(f"✅ Migration complete!")
        print(f"   Form ID: {form.id}")
        print(f"   Scale questions: {len(QUESTIONS)}")
        print(f"   Open text questions: {len(OPEN_TEXT_QUESTIONS)}")
        print(f"   Total questions: {len(QUESTIONS) + len(OPEN_TEXT_QUESTIONS)}")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
