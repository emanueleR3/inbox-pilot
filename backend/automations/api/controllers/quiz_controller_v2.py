"""
Quiz Controller V2 - Simplified State Machine Approach

This controller handles the quiz API endpoints using a simple
state machine pattern instead of LangGraph.
"""

from fastapi import HTTPException, status
from typing import Dict, Any, Optional

from api.services.quiz_service_v2 import (
    create_session_for_email,
    get_session,
    delete_session,
    fetch_quiz_session_row,
    fetch_latest_quiz_session_row_for_email,
    list_quiz_sessions,
    start_quiz,
    submit_answer,
    force_finish_quiz,
    trigger_save_pipeline,
    get_save_pipeline_status,
)


class QuizControllerV2:
    """Controller for the simplified quiz system."""
    
    async def start_quiz(self, email: str) -> Dict[str, Any]:
        """
        Start a new quiz session.
        
        Args:
            email: subscription_services.email
            
        Returns:
            Dictionary with session info and initial question
        """
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email è richiesto"
            )
        
        try:
            # Create session
            session_id, resolved_service_id = create_session_for_email(email)
            
            # Start the quiz flow
            result = await start_quiz(resolved_service_id, session_id)
            
            return {
                "session_id": result["session_id"],
                "question": result["question"],
                "bullet_list": result["bullet_list"],
                "phase": result["phase"],
                "turn_count": result["turn_count"],
                "max_turns": result["max_turns"],
                "has_context": result["has_qdrant_collection"],
                "done": result["is_done"],
                "email": result.get("email"),
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante l'avvio del quiz: {str(e)}"
            )
    
    async def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        """
        Submit an answer to the current question.
        
        Args:
            session_id: The session ID
            answer: The user's answer
            
        Returns:
            Dictionary with next question or completion status
        """
        if not session_id or not answer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID e risposta sono obbligatori"
            )
        
        try:
            flow = get_session(session_id)
            if not flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
            
            # Submit the answer
            result = await submit_answer(session_id, answer)
            
            return {
                "done": result["is_done"],
                "question": result["question"],
                "bullet_list": result["bullet_list"],
                "phase": result["phase"],
                "turn_count": result["turn_count"],
                "max_turns": result["max_turns"],
                "extracted_markdown": result.get("final_markdown"),
                "error": result.get("error"),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante l'invio della risposta: {str(e)}"
            )
    
    async def get_state(self, email: str) -> Dict[str, Any]:
        """
        Get the current state of a quiz session.
        
        Args:
            email: subscription_services.email
            
        Returns:
            Dictionary with current session state
        """
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email è richiesto"
            )
        
        try:
            row = fetch_latest_quiz_session_row_for_email(email=email, status="in_progress")
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Quiz non ancora configurato per questa email"
                )

            session_id = str(row.get("session_id") or "").strip()
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Quiz non ancora configurato per questa email"
                )

            flow = get_session(session_id)
            if not flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
            
            state = flow.get_state()
            if not state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quiz non ancora avviato"
                )
            
            return {
                "session_id": session_id,
                "service_id": row.get("service_id"),
                "email": row.get("email"),
                "phase": state["phase"],
                "turn_count": state["turn_count"],
                "max_turns": state["max_turns"],
                "business_field": state.get("business_field"),
                "bullet_list": [
                    {"name": item["name"], "completed": item["completed"], "info": item.get("info")}
                    for item in state.get("bullet_list", [])
                ],
                "messages": state["messages"],
                "is_done": state["is_done"],
                "has_context": state.get("has_qdrant_collection", False),
                "final_markdown": state.get("final_markdown"),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero dello stato: {str(e)}"
            )
    
    async def finish_quiz(self, session_id: str) -> Dict[str, Any]:
        """
        Force finish the quiz and generate final markdown.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with final markdown
        """
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID è richiesto"
            )
        
        try:
            flow = get_session(session_id)
            if not flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
            
            # Force finish the quiz
            result = await force_finish_quiz(session_id)
            
            return {
                "done": True,
                "extracted_markdown": result.get("final_markdown"),
                "bullet_list": result["bullet_list"],
                "error": result.get("error"),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante la conclusione del quiz: {str(e)}"
            )
    
    def list_sessions(self) -> list:
        """
        List all active quiz sessions.
        
        Returns:
            List of session IDs
        """
        try:
            return list_quiz_sessions(limit=50, status="in_progress")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero delle sessioni: {str(e)}"
            )

    async def save_context(self, session_id: str) -> Dict[str, Any]:
        """
        Manually trigger the save pipeline for a quiz session.
        
        This allows frontend to trigger save without relying on 
        chat message interpretation.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with started status
        """
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID è richiesto"
            )
        
        try:
            result = await trigger_save_pipeline(session_id)
            
            if not result.get("started"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("error", "Impossibile avviare il salvataggio")
                )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante l'avvio del salvataggio: {str(e)}"
            )
    
    def get_save_status(
        self, 
        session_id: Optional[str] = None, 
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a save pipeline operation from database.
        
        Multi-pod safe: reads from quiz_sessions table.
        
        Args:
            session_id: The session ID (optional)
            email: User email (optional, used if session_id not provided)
            
        Returns:
            Dictionary with save status
        """
        if not session_id and not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID o email è richiesto"
            )
        
        try:
            status_data = get_save_pipeline_status(session_id=session_id, email=email)
            
            if not status_data:
                # Session not found in DB
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sessione non trovata"
                )
            
            return status_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero dello stato di salvataggio: {str(e)}"
            )
        
    def get_sessions(self, email: str) -> Dict[str, Any]:
        """
        Get the quiz session for a given email.
        
        Args:
            email: subscription_services.email
        Returns:
            Dictionary with session details
        """
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email è richiesto"
            )
        
        try:
            row = fetch_latest_quiz_session_row_for_email(email=email)
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nessuna sessione trovata per questa email"
                )
            
            return {
                "session_id": row.get("session_id"),
                "service_id": row.get("service_id"),
                "phase": row.get("phase"),
                "business_field": row.get("business_field"),
                "bullet_list": row.get("bullet_list"),
                "is_done": row.get("is_done"),
                "has_context": row.get("has_qdrant_collection", False),
                "final_markdown": row.get("final_markdown"),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Errore durante il recupero della sessione: {str(e)}"
            )
