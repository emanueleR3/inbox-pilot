from supabase import Client
from src.core.database import get_supabase_client
from typing import Optional

class QuizSessionDAO:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_session_by_id(self, session_id: str) -> Optional[dict]:
        response = self.supabase.table("quiz_sessions").select("*").eq("session_id", session_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    
    def update_final_markdown(self, session_id: str, final_markdown: str) -> Optional[dict]:
        response = self.supabase.table("quiz_sessions").update(
            {"final_markdown": final_markdown}
        ).eq("session_id", session_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None