from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os, dotenv
import asyncio
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from dataclasses import dataclass

from langchain.tools import tool, ToolRuntime
from langchain_core.runnables import RunnableConfig


dotenv.load_dotenv()

supabase_project_id = "wobdlrcmnryeubvkqigp"
supabase_password = os.getenv("SUPABASE_PASSWORD")
DB_URI = f"postgresql://postgres:{supabase_password}@db.{supabase_project_id}.supabase.co:5432/postgres?sslmode=disable"


# Define the state schema for the graph
class GraphState(TypedDict):
    """State schema for the chatbot graph."""
    messages: Annotated[list, add_messages]


#TODO(Marcelo): Integrate real user context
@dataclass 
class UserContext:
    user_name: str
    user_email: str
    user_email_password: str 
    user_smtp_host: str
    user_smtp_port: int


def fetch_user_data(runtime: ToolRuntime[UserContext]) -> str:
    """Fetch user-specific data."""
    user_name = runtime.context.user_name
    user_email = runtime.context.user_email
    return f"Data from user {user_name}"#, User Email: {user_email}"

agent_prompt = """You are a helpful customer support chatbot that uses tools provided by Jerry MCP server to assist customers with their inquiries. Use the tools as needed to provide accurate and helpful responses."""


async def create_chatbot_agent():
    """Initialize and return the chatbot agent with Jerry MCP tools."""
    client = MultiServerMCPClient(  
        {
            "jerry": {
                "transport": "streamable_http",  # HTTP-based remote server
                "url": "http://localhost:6969/mcp",  # URL of the Jerry MCP server
            }
        }
    )

    # Create ChatOpenAI model instance
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from Jerry MCP server.") 
    
    agent = create_agent(
        model,
        tools=tools + [fetch_user_data],
        context_schema=UserContext
    )
    
    return agent


async def run_chatbot(graph: StateGraph, config: RunnableConfig):
    print("Dentro run_chatbot")
    # Pass parameters when invoking
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Send an email to customer@example.com saying Waglioooo! From Marco (get the email from user_data context)"}]},
        context=UserContext(user_name="Marco", user_email="student1@example.com", user_email_password="M2a0r0c2o!", user_smtp_host="mail.polito.it", user_smtp_port=587),
        config=config
    )
    print("Result:", result)

async def chatbot_node(state: GraphState):
    """Main chatbot node that processes messages."""
    agent = await create_chatbot_agent()
    
    # Get the last user message
    messages = state["messages"]
    
    print("dentro chatbot node, messages:", messages)
    # Invoke the agent with the messages
    response = await agent.ainvoke(
        {"messages": messages},
        context=UserContext(
            user_name="Marco", 
            user_email="student1@example.com", 
            user_email_password="M2a0r0c2o!", 
            user_smtp_host="mail.polito.it", 
            user_smtp_port=587
        )
    )
    
    return {"messages": response["messages"]}


async def main():
    # Eventual upgrade to redis or other 
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:  
        await checkpointer.setup()
        
        # Create the graph with proper state schema
        builder = StateGraph(GraphState)
        
        # Add nodes
        builder.add_node("chatbot", chatbot_node)
        
        # Add edges - this fixes the "Graph must have an entrypoint" error
        builder.add_edge(START, "chatbot")
        builder.add_edge("chatbot", END)
        
        # Compile the graph
        graph = builder.compile(checkpointer=checkpointer)

        thread_id = "1"
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        await run_chatbot(graph, config)
if __name__ == "__main__":
    asyncio.run(main())