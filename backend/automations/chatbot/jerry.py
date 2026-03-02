from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import os, dotenv
import threading
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from uuid import uuid4
from psycopg import OperationalError
from psycopg_pool import ConnectionPool
from automations.chatbot.tools import (
    send_email,
    create_draft_email,
    retrieve_last_n_emails,
    search_emails,
    get_thread_messages,
    delete_emails,
    forward_email,
    reply_to_email,
    schedule_or_propose_meeting,
    search_email_attachments,
)
from automations.chatbot.db.db import get_user_context
from automations.chatbot.prompts import JERRY_AGENT_PROMPT, build_enriched_prompt
from langchain_core.runnables import RunnableConfig

from langchain_core.messages import HumanMessage, SystemMessage

'''
https://chatgpt.com/share/69248492-957c-800f-946c-f9039e4783f3
'''

dotenv.load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_PROJECT_JERRY"] = os.getenv("LANGCHAIN_PROJECT_JERRY", "default")

supabase_project_id = os.getenv("SUPABASE_PROJECT_ID")
supabase_password = os.getenv("SUPABASE_PASSWORD")
DB_URI = f"postgresql://postgres.{supabase_project_id}:{supabase_password}@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

# Re-export for backwards compatibility
agent_prompt = JERRY_AGENT_PROMPT

class GraphState(TypedDict):
    """State schema for the chatbot graph."""
    messages: Annotated[list, add_messages]


def _build_system_prompt_with_context(user_id: str) -> str:
    """
    Build the system prompt with user context from Supabase.
    
    Args:
        user_id: The user identifier
        
    Returns:
        System prompt enriched with user context
    """
    user_context = get_user_context(user_id)
    
    if not user_context:
        print(f"⚠️ [JERRY] No user context found for user_id: {user_id}, using base prompt")
    else:
        print(f"✅ [JERRY] System prompt enriched with user context for user_id: {user_id}")
    
    return build_enriched_prompt(user_context)


def handle_user_message(user_id: str, thread_id: str | None, text: str):
    # Content moderation check BEFORE any LLM processing
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        moderation_response = client.moderations.create(
            model="omni-moderation-latest",
            input=text
        )
        
        result = moderation_response.results[0]
        if result.flagged:
            # Log flagged categories
            try:
                categories_dict = result.categories.model_dump()
            except AttributeError:
                categories_dict = dict(result.categories)
            
            flagged_categories = [cat for cat, flagged in categories_dict.items() if flagged]
            print(f"🚨 [JERRY_MODERATION] Content FLAGGED! Categories: {flagged_categories}")
            
            # Return immediately with error message - don't pass to any LLM
            class ModerationBlockedMessage:
                content = "Non posso elaborare richieste di questo genere."
            
            # Return thread_id (create if needed) and blocked message
            if thread_id is None:
                thread_id = f"user{user_id}:conv{uuid4()}"
            return thread_id, ModerationBlockedMessage()
        
        print(f"✅ [JERRY_MODERATION] Content passed moderation check")
        
    except Exception as e:
        print(f"❌ [JERRY_MODERATION] Error during moderation check: {e}")
        # On error, continue but log for monitoring

    # Nel caso non esista thread_id, ne crea uno nuovo con user context.
    # Tuttavia, dovrebbe essere sempre gia' presente, perche' gestito a livello di API.
    with graph_session() as graph:
        if thread_id is None:
            system_prompt = _build_system_prompt_with_context(user_id)
            thread_id = f"user{user_id}:conv{uuid4()}"

            config = {"configurable": {"thread_id": thread_id}}
            graph.invoke(
                {"messages": [SystemMessage(content=system_prompt)]},
                config=config,
            )

        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(
            {"messages": [HumanMessage(content=text)]},
            config=config,
        )

        answer = result["messages"][-1]
        return thread_id, answer


def create_chatbot_agent(state: GraphState):
    """Initialize and return the chatbot agent with tools."""
    
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    tools = [
        send_email,
        create_draft_email,
        retrieve_last_n_emails,
        search_emails,
        get_thread_messages,
        delete_emails,
        forward_email,
        reply_to_email,
        schedule_or_propose_meeting,
        search_email_attachments,
    ]
    
    agent = create_agent(
        model,
        tools=tools,
    )
    
    return agent


_pool_lock = threading.Lock()
_pool: ConnectionPool | None = None
_checkpoint_setup_done = False


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        max_size = int(os.getenv("JERRY_DB_POOL_MAX_SIZE", "5"))
        timeout = float(os.getenv("JERRY_DB_POOL_TIMEOUT_SECONDS", "30"))

        _pool = ConnectionPool(
            conninfo=DB_URI,
            min_size=0,
            max_size=max_size,
            timeout=timeout,
            kwargs={"autocommit": True},
        )
        return _pool


def _reset_pool() -> None:
    global _pool, _checkpoint_setup_done
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
        _pool = None
        _checkpoint_setup_done = False


def _compile_graph(checkpointer: PostgresSaver):
    builder = StateGraph(GraphState)
    builder.add_node("chatbot", create_chatbot_agent)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=checkpointer)


@contextmanager
def graph_session():
    """Yield a compiled graph bound to a fresh, pooled DB connection.

    This prevents long-lived stale connections that can lead to
    OperationalError('the connection is closed') in production.
    """
    last_error: OperationalError | None = None

    for attempt in range(2):
        pool = _get_pool()
        try:
            with pool.connection() as conn:
                checkpointer = PostgresSaver(conn)

                global _checkpoint_setup_done
                if not _checkpoint_setup_done:
                    with _pool_lock:
                        if not _checkpoint_setup_done:
                            checkpointer.setup()
                            _checkpoint_setup_done = True

                graph = _compile_graph(checkpointer)
                yield graph
                return
        except OperationalError as e:
            last_error = e
            if attempt == 0 and "connection is closed" in str(e).lower():
                _reset_pool()
                continue
            raise

    if last_error is not None:
        raise last_error



if __name__ == "__main__":
    
    result = handle_user_message(
        user_id="6990",
        thread_id=None,
        text="Send an email from dev4@example.com to customer@example.com with subject 'Test' and body 'This is a test email to verify the functionality!'"
    )
    
    print("\nChatbot response:", result[1].content)
    print("\nThread ID:", result[0])
    print("\nWhole result:", result)