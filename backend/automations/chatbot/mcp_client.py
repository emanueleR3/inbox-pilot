from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import os, dotenv
import asyncio

dotenv.load_dotenv()

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

    tools = await client.get_tools() 
    print(f"Loaded {len(tools)} tools from Jerry MCP server.") 
    
    # Create ChatOpenAI model instance
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    
    agent = create_agent(
        model,
        tools
    )
    
    return agent


async def chat(agent, message: str):
    """Send a message to the chatbot and get a response."""
    try:
        response = await agent.ainvoke({"messages": [
            {"role": "system", "content": agent_prompt}, 
            {"role": "user", "content": message}
            ]
        },
        context={"user_role": "customer"})

        '''' RESPONSE EXAMPLE
        {'messages': [SystemMessage(content='You are a helpful customer support chatbot that uses tools provided by Jerry MCP server to assist customers with their inquiries. Use the tools as needed to provide accurate and helpful responses.', additional_kwargs={}, response_metadata={}, id='41f137f9-8c7d-4329-9ca9-15cc1a5869f4'), HumanMessage(content='Ciao, cosa pozzo fare?', additional_kwargs={}, response_metadata={}, id='06bc84d8-71b4-4142-8123-3c08e609f1f7'), AIMessage(content='Ciao! Come posso aiutarti oggi? Se hai domande o hai bisogno di assistenza, fammi sapere!', additional_kwargs={'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 25, 'prompt_tokens': 89, 'total_tokens': 114, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_provider': 'openai', 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_51db84afab', 'id': 'chatcmpl-Ccz2gIWil60tNjtqUuc3s12ZlBTFy', 'service_tier': 'default', 'finish_reason': 'stop', 'logprobs': None}, id='lc_run--747f7817-416c-43b3-801f-be7e236dc1a6-0', usage_metadata={'input_tokens': 89, 'output_tokens': 25, 'total_tokens': 114, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}})]}
        '''
        return response["messages"][-1].content
    except Exception as e:
        return f"Error: {str(e)}"


async def run_chatbot():
    """Run an interactive chatbot session."""
    print("Chatbot initialized with Jerry MCP tools.")
    print("Type 'exit', 'quit', or 'bye' to end the conversation.\n")
    
    agent = await create_chatbot_agent()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Goodbye!")
                break
            
            response = await chat(agent, user_input)
            print(f"Bot: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(run_chatbot())