"""
Save Pipeline Service - Background context save with DB-persisted status tracking.

This service handles:
1. Background execution of the save pipeline
2. Status tracking persisted to quiz_sessions table (multi-pod safe)
3. Atomic compare-and-set to prevent duplicate executions
"""
import threading
import uuid
import os
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from db_client import get_supabase_client


class SavePhase(str, Enum):
    """Phases of the save pipeline."""
    IDLE = "idle"
    PENDING = "PENDING"
    FETCHING_DATA = "FETCHING_DATA"
    READING_JSON = "READING_JSON"
    UPDATING_JSON_WITH_LLM = "UPDATING_JSON_WITH_LLM"
    SAVING_JSON = "SAVING_JSON"
    DELETING_OLD_COLLECTION = "DELETING_OLD_COLLECTION"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    UPLOADING_TO_QDRANT = "UPLOADING_TO_QDRANT"
    UPDATING_DATABASE = "UPDATING_DATABASE"
    COMPLETED = "completed"
    FAILED = "failed"


# Save status values for DB
SAVE_STATUS_IDLE = "idle"
SAVE_STATUS_RUNNING = "running"
SAVE_STATUS_COMPLETED = "completed"
SAVE_STATUS_FAILED = "failed"

# Total number of steps (excluding PENDING, COMPLETED, FAILED)
TOTAL_STEPS = 9

# Columns to select for save status
_SAVE_STATUS_COLUMNS = (
    "session_id,email,"
    "save_status,save_phase,save_total_steps,save_actual_step,"
    "save_error,save_started_at,save_updated_at,save_completed_at,"
    "save_details,save_run_id,save_worker"
)


def _get_worker_id() -> str:
    """Get a unique identifier for this worker/pod."""
    hostname = socket.gethostname()
    pid = os.getpid()
    return f"{hostname}:{pid}"


def _normalize_session_id(session_id: str) -> str:
    """Normalize session ID string."""
    if session_id is None:
        return ""
    return str(session_id).strip().strip('"').strip("'")


def _normalize_email(email: str) -> str:
    """Normalize email string."""
    if email is None:
        return ""
    return str(email).strip().strip('"').strip("'").lower()


def _update_save_status_in_db(
    session_id: str,
    save_status: str,
    save_phase: str,
    save_actual_step: int,
    save_error: Optional[str] = None,
    save_details: Optional[Dict[str, Any]] = None,
    save_completed_at: Optional[datetime] = None,
    save_run_id: Optional[str] = None,
    save_started_at: Optional[datetime] = None,
) -> bool:
    """
    Update save status columns in quiz_sessions table.
    
    Args:
        session_id: The quiz session ID
        save_status: Status value (idle, running, completed, failed)
        save_phase: Current phase name
        save_actual_step: Current step number
        save_error: Error message if failed
        save_details: Additional details dict
        save_completed_at: Completion timestamp
        save_run_id: Unique run identifier
        save_started_at: Start timestamp
        
    Returns:
        True if update succeeded
    """
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    
    if not session_id:
        return False
    
    update_data: Dict[str, Any] = {
        "save_status": save_status,
        "save_phase": save_phase,
        "save_actual_step": save_actual_step,
        "save_updated_at": datetime.now().isoformat(),
        "save_worker": _get_worker_id(),
    }
    
    if save_error is not None:
        update_data["save_error"] = save_error
    
    if save_details is not None:
        update_data["save_details"] = save_details
    
    if save_completed_at is not None:
        update_data["save_completed_at"] = save_completed_at.isoformat()
    
    if save_run_id is not None:
        update_data["save_run_id"] = save_run_id
    
    if save_started_at is not None:
        update_data["save_started_at"] = save_started_at.isoformat()
    
    try:
        supabase.table("quiz_sessions").update(update_data).eq("session_id", session_id).execute()
        return True
    except Exception as e:
        print(f"❌ [SAVE_PIPELINE] Failed to update save status in DB: {e}")
        return False


def _try_acquire_save_lock(session_id: str, run_id: str) -> bool:
    """
    Try to acquire the save lock using atomic compare-and-set.
    
    Only starts if save_status is not 'running'.
    This prevents multiple pods from running the same save pipeline.
    
    Args:
        session_id: The quiz session ID
        run_id: Unique run identifier
        
    Returns:
        True if lock acquired, False if already running
    """
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    
    if not session_id:
        return False
    
    now = datetime.now()
    
    try:
        # Atomic update: only update if save_status is NOT 'running'
        result = (
            supabase.table("quiz_sessions")
            .update({
                "save_status": SAVE_STATUS_RUNNING,
                "save_phase": SavePhase.PENDING.value,
                "save_actual_step": 0,
                "save_total_steps": TOTAL_STEPS,
                "save_error": None,
                "save_started_at": now.isoformat(),
                "save_updated_at": now.isoformat(),
                "save_completed_at": None,
                "save_details": {},
                "save_run_id": run_id,
                "save_worker": _get_worker_id(),
            })
            .eq("session_id", session_id)
            .neq("save_status", SAVE_STATUS_RUNNING)
            .execute()
        )
        
        # Check if any row was updated
        # Supabase returns the updated rows in result.data
        if result.data and len(result.data) > 0:
            print(f"✅ [SAVE_PIPELINE] Lock acquired for session {session_id}, run_id={run_id}")
            return True
        else:
            print(f"⚠️ [SAVE_PIPELINE] Lock NOT acquired - pipeline already running for session {session_id}")
            return False
            
    except Exception as e:
        print(f"❌ [SAVE_PIPELINE] Error acquiring lock: {e}")
        return False


def get_save_status_from_db(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get save status from database by session_id.
    
    Args:
        session_id: The quiz session ID
        
    Returns:
        Save status dict or None if not found
    """
    supabase = get_supabase_client()
    session_id = _normalize_session_id(session_id)
    
    if not session_id:
        return None
    
    try:
        result = (
            supabase.table("quiz_sessions")
            .select(_SAVE_STATUS_COLUMNS)
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


def get_save_status_from_db_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get save status from database by email (finds the latest session).
    
    Args:
        email: User email
        
    Returns:
        Save status dict or None if not found
    """
    supabase = get_supabase_client()
    email = _normalize_email(email)
    
    if not email:
        return None
    
    try:
        result = (
            supabase.table("quiz_sessions")
            .select(_SAVE_STATUS_COLUMNS)
            .eq("email", email)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def db_row_to_status_dict(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Convert database row to status dict for API response.
    
    Args:
        row: Database row dict
        
    Returns:
        Status dict for API response
    """
    if not row:
        return None
    
    save_status = row.get("save_status", SAVE_STATUS_IDLE)
    save_phase = row.get("save_phase")
    
    return {
        "session_id": str(row.get("session_id", "")),
        "email": row.get("email", ""),
        "phase": save_phase,
        "actual_step": row.get("save_actual_step", 0),
        "total_steps": row.get("save_total_steps", TOTAL_STEPS),
        "started_at": row.get("save_started_at"),
        "updated_at": row.get("save_updated_at"),
        "completed_at": row.get("save_completed_at"),
        "error": row.get("save_error"),
        "details": row.get("save_details") or {},
        "run_id": str(row.get("save_run_id", "")) if row.get("save_run_id") else None,
        "worker": row.get("save_worker"),
        "is_running": save_status == SAVE_STATUS_RUNNING,
        "is_completed": save_status == SAVE_STATUS_COMPLETED,
        "is_failed": save_status == SAVE_STATUS_FAILED,
        "save_status": save_status,
    }


def run_save_pipeline_background(
    session_id: str,
    email: str,
    conversation_log: List[str],
    final_markdown: str
) -> bool:
    """
    Start the save pipeline in a background thread.
    
    Uses atomic compare-and-set to prevent duplicate executions across pods.
    
    Args:
        session_id: The quiz session ID
        email: User email
        conversation_log: List of change log entries
        final_markdown: Final confirmed markdown
        
    Returns:
        True if pipeline was started, False if already running
    """
    session_id = _normalize_session_id(session_id)
    run_id = str(uuid.uuid4())
    
    # Try to acquire lock (atomic compare-and-set)
    if not _try_acquire_save_lock(session_id, run_id):
        return False
    
    # Start background thread
    thread = threading.Thread(
        target=_run_pipeline_sync,
        args=(session_id, email, conversation_log, final_markdown, run_id),
        daemon=True
    )
    thread.start()
    
    print(f"🚀 [SAVE_PIPELINE] Started background pipeline for session {session_id}, run_id={run_id}")
    return True


def _update_status(
    session_id: str,
    phase: SavePhase,
    step: int,
    error: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    is_completed: bool = False,
    is_failed: bool = False
) -> None:
    """
    Update save status in database.
    
    Args:
        session_id: The quiz session ID
        phase: Current phase
        step: Current step number
        error: Error message if failed
        details: Additional details
        is_completed: Whether pipeline completed successfully
        is_failed: Whether pipeline failed
    """
    if is_completed:
        save_status = SAVE_STATUS_COMPLETED
        completed_at = datetime.now()
    elif is_failed:
        save_status = SAVE_STATUS_FAILED
        completed_at = datetime.now()
    else:
        save_status = SAVE_STATUS_RUNNING
        completed_at = None
    
    _update_save_status_in_db(
        session_id=session_id,
        save_status=save_status,
        save_phase=phase.value,
        save_actual_step=step,
        save_error=error,
        save_details=details,
        save_completed_at=completed_at,
    )


def _run_pipeline_sync(
    session_id: str,
    email: str,
    conversation_log: List[str],
    final_markdown: str,
    run_id: str
) -> None:
    """
    Synchronous pipeline execution (runs in background thread).
    
    This is a modified version of finalize_context_update that reports progress to DB.
    """
    from datetime import datetime as dt
    
    try:
        from db_client import get_scraping_data, update_scraping_paths
        from quiz.flow.context_updater import (
            read_scraping_json,
            update_json_with_llm,
            save_updated_json,
            chunk_pages,
            embed_and_upload_to_qdrant,
            delete_qdrant_collection,
        )
    except ImportError as e:
        _update_status(session_id, SavePhase.FAILED, 0, error=f"Import error: {e}", is_failed=True)
        return
    
    SCRAPINGS_DIR = os.getenv("SCRAPINGS_DIR", "/app/scrapings")
    SCRAPINGS_DB_DIR = os.getenv("SCRAPINGS_DB_DIR", "/home/deploy/corretto/data/scrapings")
    
    print(f"\n{'='*60}")
    print(f"🔄 [SAVE_PIPELINE] Starting context update for: {email}")
    print(f"   Run ID: {run_id}")
    print(f"   Worker: {_get_worker_id()}")
    print(f"{'='*60}")
    
    try:
        # Step 1: Fetch scraping data from DB
        _update_status(session_id, SavePhase.FETCHING_DATA, 1, details={"message": "Recupero dati scraping dal database"})
        scraping_data = get_scraping_data(email)
        if not scraping_data:
            _update_status(session_id, SavePhase.FAILED, 1, error=f"Nessun dato di scraping trovato per: {email}", is_failed=True)
            return
        
        original_json_path = scraping_data.get("scraping_collection_path")
        old_collection_name = scraping_data.get("qdrant_collection")
        
        if not original_json_path:
            _update_status(session_id, SavePhase.FAILED, 1, error="scraping_collection_path non presente nel database", is_failed=True)
            return
        
        print(f"📄 Original JSON path: {original_json_path}")
        print(f"📦 Old collection: {old_collection_name}")
        
        # Step 2: Read original JSON
        _update_status(session_id, SavePhase.READING_JSON, 2, details={"message": "Lettura JSON originale", "path": original_json_path})
        original_json = read_scraping_json(original_json_path)
        if not original_json:
            _update_status(session_id, SavePhase.FAILED, 2, error="Impossibile leggere il JSON originale", is_failed=True)
            return
        
        # Step 3: Update JSON with LLM
        _update_status(session_id, SavePhase.UPDATING_JSON_WITH_LLM, 3, details={"message": "Aggiornamento JSON con LLM in corso..."})
        updated_json = update_json_with_llm(original_json, conversation_log, final_markdown)
        if not updated_json:
            _update_status(session_id, SavePhase.FAILED, 3, error="LLM non è riuscito ad aggiornare il JSON", is_failed=True)
            return
        
        # Step 4: Save updated JSON
        _update_status(session_id, SavePhase.SAVING_JSON, 4, details={"message": "Salvataggio JSON aggiornato"})
        new_json_path = save_updated_json(original_json_path, updated_json)
        if not new_json_path:
            _update_status(session_id, SavePhase.FAILED, 4, error="Impossibile salvare il JSON aggiornato", is_failed=True)
            return
        
        # Step 5: Delete old Qdrant collection
        _update_status(session_id, SavePhase.DELETING_OLD_COLLECTION, 5, details={"message": f"Eliminazione collezione {old_collection_name}"})
        if old_collection_name:
            delete_qdrant_collection(old_collection_name)
        
        # Step 6: Chunk the pages
        _update_status(session_id, SavePhase.CHUNKING, 6, details={"message": "Creazione chunks dal JSON"})
        chunks = chunk_pages(updated_json)
        if not chunks:
            _update_status(session_id, SavePhase.FAILED, 6, error="Nessun chunk creato dal JSON", is_failed=True)
            return
        
        _update_status(session_id, SavePhase.CHUNKING, 6, details={"message": f"Creati {len(chunks)} chunks", "chunks_count": len(chunks)})
        
        # Step 7: Generate new collection name
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        email_safe = email.replace("@", "_at_").replace(".", "_")
        new_collection_name = f"quiz_updated_{email_safe}_{timestamp}"
        
        # Step 8: Embed chunks
        _update_status(session_id, SavePhase.EMBEDDING, 7, details={"message": f"Embedding di {len(chunks)} chunks in corso...", "chunks_count": len(chunks)})
        
        # Step 9: Upload to Qdrant
        _update_status(session_id, SavePhase.UPLOADING_TO_QDRANT, 8, details={"message": f"Upload su Qdrant: {new_collection_name}"})
        success, points_count = embed_and_upload_to_qdrant(chunks, new_collection_name)
        if not success:
            _update_status(session_id, SavePhase.FAILED, 8, error="Upload su Qdrant fallito", is_failed=True)
            return
        
        _update_status(session_id, SavePhase.UPLOADING_TO_QDRANT, 8, details={
            "message": f"Caricati {points_count} punti su Qdrant",
            "points_count": points_count,
            "collection_name": new_collection_name
        })
        
        # Step 10: Update DB with new paths
        _update_status(session_id, SavePhase.UPDATING_DATABASE, 9, details={"message": "Aggiornamento database"})
        new_json_path_for_db = os.path.join(SCRAPINGS_DB_DIR, os.path.basename(new_json_path))
        
        if not update_scraping_paths(email, new_json_path_for_db, new_collection_name):
            _update_status(session_id, SavePhase.FAILED, 9, error="Aggiornamento percorsi nel database fallito", is_failed=True)
            return
        
        # Mark as completed
        _update_status(
            session_id, 
            SavePhase.COMPLETED, 
            TOTAL_STEPS, 
            details={
                "message": "Salvataggio completato con successo",
                "new_json_path": new_json_path,
                "new_collection_name": new_collection_name,
                "points_count": points_count
            },
            is_completed=True
        )
        
        print(f"\n{'='*60}")
        print(f"✅ [SAVE_PIPELINE] Context update completed successfully!")
        print(f"   New JSON: {new_json_path}")
        print(f"   New collection: {new_collection_name}")
        print(f"   Run ID: {run_id}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ [SAVE_PIPELINE] Error: {e}")
        _update_status(session_id, SavePhase.FAILED, 0, error=str(e), is_failed=True)


def reset_save_status(session_id: str) -> bool:
    """
    Reset save status to idle.
    
    Useful for retrying after a failure.
    
    Args:
        session_id: The quiz session ID
        
    Returns:
        True if reset succeeded
    """
    return _update_save_status_in_db(
        session_id=session_id,
        save_status=SAVE_STATUS_IDLE,
        save_phase=SavePhase.IDLE.value,
        save_actual_step=0,
        save_error=None,
        save_details={},
    )


__all__ = [
    "SavePhase",
    "SAVE_STATUS_IDLE",
    "SAVE_STATUS_RUNNING",
    "SAVE_STATUS_COMPLETED",
    "SAVE_STATUS_FAILED",
    "TOTAL_STEPS",
    "run_save_pipeline_background",
    "get_save_status_from_db",
    "get_save_status_from_db_by_email",
    "db_row_to_status_dict",
    "reset_save_status",
]
