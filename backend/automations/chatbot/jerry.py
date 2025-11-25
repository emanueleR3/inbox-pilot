from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import os, dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from uuid import uuid4
from automations.chatbot.tools import send_email
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
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "default")

supabase_project_id = os.getenv("SUPABASE_PROJECT_ID")
supabase_password = os.getenv("SUPABASE_PASSWORD")
DB_URI = f"postgresql://postgres.{supabase_project_id}:{supabase_password}@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

agent_prompt = """
You are Jerry, a helpful customer support chatbot that assists the customer and uses its tools to address their requests. 
Use the tools as needed to execute what the customer asks for.
"""

class GraphState(TypedDict):
    """State schema for the chatbot graph."""
    messages: Annotated[list, add_messages]


def handle_user_message(user_id: str, thread_id: str | None, text: str):
    # Nel caso non esista thread_id, ne crea uno nuovo. Tuttavia, dovrebbe essere sempre gia' presente, perche' gestito a livello di API.
    if thread_id is None:
        messages = [
            SystemMessage(agent_prompt),
        ]
        thread_id = f"user{user_id}:conv{uuid4()}"

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
    ]
    
    agent = create_agent(
        model,
        tools=tools,
    )
    
    return agent

checkpointer_cm = PostgresSaver.from_conn_string(DB_URI)
checkpointer = checkpointer_cm.__enter__()
checkpointer.setup()

builder = StateGraph(GraphState)

builder.add_node("chatbot", create_chatbot_agent)

builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

graph = builder.compile(checkpointer=checkpointer)



if __name__ == "__main__":
    
    result = handle_user_message(
        user_id="6990",
        thread_id=None,
        text="Send an email from dev4@example.com to customer@example.com with subject 'Test' and body 'This is a test email to verify the functionality!'"
    )
    
    print("\nChatbot response:", result[1].content)
    print("\nThread ID:", result[0])
    print("\nWhole result:", result)