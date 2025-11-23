from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import os, dotenv
import asyncio
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from tools import send_email
from langchain_core.runnables import RunnableConfig


dotenv.load_dotenv()

supabase_project_id = os.getenv("SUPABASE_PROJECT_ID")
supabase_password = os.getenv("SUPABASE_PASSWORD")
DB_URI = f"postgresql://postgres:{supabase_password}@db.{supabase_project_id}.supabase.co:5432/postgres?sslmode=disable"


# Define the state schema for the graph
class GraphState(TypedDict):
    """State schema for the chatbot graph."""
    messages: Annotated[list, add_messages]

agent_prompt = """
You are a helpful customer support chatbot that assists the customer and uses its tools to address their requests. 
Use the tools as needed to execute what the customer asks for.
"""


async def create_chatbot_agent(state: GraphState):
    """Initialize and return the chatbot agent with tools."""
    
    # Create ChatOpenAI model instance
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    tools = [send_email]
    
    agent = create_agent(
        model,
        tools=tools,
    )
    
    return agent

async def main():
    # Eventual upgrade to redis or other 
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:  
        await checkpointer.setup()
        
        # Create the graph with proper state schema
        builder = StateGraph(GraphState)
        
        # Add nodes
        builder.add_node("chatbot", create_chatbot_agent)
        
        # Add edges - this fixes the "Graph must have an entrypoint" error
        builder.add_edge(START, "chatbot")
        builder.add_edge("chatbot", END)
        
        # Compile the graph
        graph = builder.compile(checkpointer=checkpointer)

        thread_id = "1"
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "Send an email from dev4@example.com to customer@example.com with subject 'Test' and body 'This is a test email to verify the functionality!'"}]},
                config=config
            )
        
        print("\n=== Result ===")
        print(result)

if __name__ == "__main__":
    asyncio.run(main())