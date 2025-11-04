from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

#automations/api/services/quiz_service.py
from automations.api.services.quiz_service import (
    create_session,
    get_session,
    delete_session,
    append_quiz_answer,
    persist_quiz_result,
    get_session_keys,
)
from automations.quiz.models import Question, Answer


router = APIRouter(tags=["quiz"])

class StartQuizRequest(BaseModel):
    service_id: str = Field(..., description="Service identifier in Supabase 'subscription_services' table")

class QuestionDTO(BaseModel):
    id: str
    text: str
    helper_text: Optional[str] = None
    order: Optional[int] = None

    @classmethod
    def from_model(cls, q: Question) -> "QuestionDTO":
        return cls(id=q.id, text=q.text, helper_text=q.helper_text, order=q.order)

class StartQuizResponse(BaseModel):
    session_id: str
    question: Optional[QuestionDTO] = None
    max_questions: int


@router.post("/start", response_model=StartQuizResponse)
async def start_quiz(req: StartQuizRequest):
    """Start a new quiz for a given company and return the first question."""
    sess = create_session(req.service_id)
    print(sess)

    # Generate first question
    question = sess.chain.generate_next_question(sess.quiz.questions, sess.quiz.answers, sess.company_info)
    if question is not None:
        qdto = QuestionDTO.from_model(question)
    else:
        qdto = None

    return StartQuizResponse(
        session_id=sess.session_id,
        question=qdto,
        max_questions=sess.chain.max_questions,
    )


class SubmitAnswerRequest(BaseModel):
    session_id: str
    value: str = Field(..., description="User answer for the last question")

class SubmitAnswerResponse(BaseModel):
    done: bool
    next_question: Optional[QuestionDTO] = None
    extracted_markdown: Optional[str] = None
    total_answers: int


@router.post("/answer", response_model=SubmitAnswerResponse)
async def submit_answer(req: SubmitAnswerRequest):
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store answer
    if not sess.quiz.questions:
        raise HTTPException(status_code=400, detail="No question to answer. Start the quiz first.")

    answer = Answer(question_id=sess.quiz.questions[-1].id, value=req.value)
    sess.quiz.answers.append(answer)
    # Persist answer to Supabase
    try:
        append_quiz_answer(sess.company_id, sess.quiz.questions[-1], answer)
    except Exception as e:
        # Don't fail the flow if persistence fails; log or continue.
        pass

    # Generate next question
    next_q = sess.chain.generate_next_question(sess.quiz.questions, sess.quiz.answers, sess.company_info)
    if next_q is None:
        # Quiz complete: extract final info
        markdown = sess.chain.extract_total_company_info(sess.company_info, sess.quiz)
        # Persist final info
        try:
            persist_quiz_result(sess.company_id, markdown)
        except Exception:
            pass
        # Optionally end the session
        delete_session(sess.session_id)
        return SubmitAnswerResponse(done=True, extracted_markdown=markdown, total_answers=len(sess.quiz.answers))

    return SubmitAnswerResponse(
        done=False,
        next_question=QuestionDTO.from_model(next_q),
        total_answers=len(sess.quiz.answers),
    )

class QuizStateResponse(BaseModel):
    session_id: str
    questions: list[QuestionDTO]
    answers: list[str]
    total: int


@router.get("/{session_id}/state", response_model=QuizStateResponse)
async def get_state(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return QuizStateResponse(
        session_id=session_id,
        questions=[QuestionDTO.from_model(q) for q in sess.quiz.questions],
        answers=[str(a.value) for a in sess.quiz.answers],
        total=len(sess.quiz.answers),
    )


class FinishQuizRequest(BaseModel):
    session_id: str

class FinishQuizResponse(BaseModel):
    extracted_markdown: str

@router.post("/finish", response_model=FinishQuizResponse, description="Force finish the quiz and extract the information immediately (normally not needed).")
async def finish_quiz(req: FinishQuizRequest):
    sess = get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    markdown = sess.chain.extract_total_company_info(sess.company_info, sess.quiz)
    try:
        persist_quiz_result(sess.company_id, markdown)
    except Exception:
        pass
    delete_session(sess.session_id)
    return FinishQuizResponse(extracted_markdown=markdown)

@router.get("/sessions", response_model=list[str], description="List all active quiz session IDs (for debugging).")
async def list_sessions():
    return list(get_session_keys())


