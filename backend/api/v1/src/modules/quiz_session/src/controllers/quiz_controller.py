from src.core.DAO.quiz_session_dao import QuizSessionDAO
from src.handler_exception import (
    MissingFieldException,
    BadRequestException,
    NotFoundException,
    APIException,
    DatabaseException
)

class QuizController:
    def __init__(self):
        self.quiz_session_dao = QuizSessionDAO()
    
    def update_final_markdown(self, payload: dict) -> dict:
        required_fields = ["session_id", "final_markdown"]
        missing_fields = [field for field in required_fields if field not in payload]
        
        if missing_fields:
            raise MissingFieldException(fields=missing_fields)
        
        session_id = payload.get("session_id")
        final_markdown = payload.get("final_markdown")
        
        if not session_id or not isinstance(session_id, str) or session_id.strip() == "":
            raise BadRequestException(detail="session_id deve essere una stringa non vuota")
        
        if final_markdown is None:
            raise BadRequestException(detail="final_markdown è obbligatorio")
        
        if not isinstance(final_markdown, str):
            raise BadRequestException(detail="final_markdown deve essere una stringa")
        
        try:
            existing_session = self.quiz_session_dao.get_session_by_id(session_id)
            
            if not existing_session:
                raise NotFoundException(detail=f"Sessione quiz con ID '{session_id}' non trovata")
            
            updated_session = self.quiz_session_dao.update_final_markdown(session_id, final_markdown)
            
            if not updated_session:
                raise DatabaseException(operation="aggiornamento final_markdown")
            
            return updated_session
        
        except APIException:
            raise
        except Exception as e:
            raise DatabaseException(operation=f"aggiornamento final_markdown: {str(e)}")
