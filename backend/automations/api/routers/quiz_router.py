from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from automations.api.controllers.quiz_controller import QuizController

router = APIRouter(tags=["internal-quiz"], include_in_schema=False)
controller = QuizController()


#class StartQuizRequest(BaseModel):
    #service_id: str = Field(..., description="Service identifier")


#class SubmitAnswerRequest(BaseModel):
    #session_id: str
    #value: str


#class FinishQuizRequest(BaseModel):
    #session_id: str


@router.post("/start")
async def start_quiz(req: dict):
    service_id = req.get("service_id")

    return controller.start_quiz(service_id)


@router.post("/answer")
async def submit_answer(req: dict):
    session_id = req.get("session_id")
    email = req.get("email")
    value = req.get("value")

    return controller.submit_answer(session_id, email, value)


@router.get("/{session_id}/state")
async def get_state(session_id: str):
    return controller.get_state(session_id)


@router.post("/finish")
async def finish_quiz(req: dict):
    email = req.get("email")
    session_id = req.get("session_id")

    return controller.finish_quiz(session_id, email)


@router.get("/sessions")
async def list_sessions():
    return controller.list_sessions()



