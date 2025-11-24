# Jerry Chatbot API

A comprehensive API for interacting with Jerry, an AI-powered customer support chatbot built with LangChain and LangGraph.

## Features

- 💬 **Send Messages**: Send messages to Jerry and receive intelligent responses
- 🌊 **Streaming Responses**: Real-time streaming of chatbot responses via Server-Sent Events
- 🧵 **Thread Management**: Create, retrieve, and delete conversation threads
- 📜 **Conversation History**: Access complete conversation history for any thread
- 🔧 **Tool Execution**: Execute tools directly or let Jerry use them naturally
- 🛠️ **Available Tools**: Currently supports email sending with more tools coming soon

## Architecture

The Jerry API follows a clean architecture pattern with three layers:

```
routers/chatbot.py          # HTTP endpoints and request validation
    ↓
controllers/jerry_controller.py  # Business logic and error handling
    ↓
services/jerry_service.py        # Core chatbot functionality
```

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL (for conversation persistence)
- OpenAI API key
- Supabase account (for database)

### Environment Variables

Create a `.env` file with the following:

```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_PROJECT_ID=your_project_id
SUPABASE_PASSWORD=your_password
ENCRYPTION_KEY_TOKEN=your_encryption_key

# LangSmith (optional, for tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=jerry-chatbot
```

### Installation

```bash
cd /Users/loriscatalano/Progetti/Corretto/Backend/automations
pip install -r requirements.txt
```

### Running the Server

```bash
cd /Users/loriscatalano/Progetti/Corretto/Backend/automations/api
python main.py
```

The API will be available at `http://localhost:8010`

## API Endpoints

### 1. Get Available Tools

Get a list of all available tools that Jerry can use.

**Endpoint:** `GET /chatbot/tools`

**Response:**
```json
{
  "tools": [
    {
      "name": "send_email",
      "description": "Send an email using Google OAuth, Microsoft OAuth, or SMTP.",
      "parameters": {
        "sender_address": "Email address of the sender",
        "receiver_address": "Email address of the recipient",
        "subject": "Email subject",
        "body": "Email body content",
        ...
      }
    }
  ],
  "count": 1
}
```

### 2. Create Thread

Create a new conversation thread.

**Endpoint:** `POST /chatbot/thread/create`

**Request Body:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "thread_id": "user123:conv<uuid>",
  "message": "Thread created successfully"
}
```

### 3. Send Message

Send a message to Jerry and receive a response.

**Endpoint:** `POST /chatbot/message`

**Request Body:**
```json
{
  "user_id": "user123",
  "message": "Hello Jerry, can you help me send an email?",
  "thread_id": "user123:conv<uuid>"  // Optional, creates new if omitted
}
```

**Response:**
```json
{
  "thread_id": "user123:conv<uuid>",
  "response": "Of course! I'd be happy to help you send an email. What would you like to send?",
  "message_type": "AIMessage"
}
```

### 4. Stream Message

Send a message and receive a streaming response.

**Endpoint:** `POST /chatbot/message/stream`

**Request Body:**
```json
{
  "user_id": "user123",
  "message": "Tell me about your capabilities",
  "thread_id": "user123:conv<uuid>"  // Optional
}
```

**Response:** Server-Sent Events stream
```
data: {"thread_id": "user123:conv<uuid>", "content": "I can help", "type": "message"}
data: {"thread_id": "user123:conv<uuid>", "content": " you with", "type": "message"}
data: {"thread_id": "user123:conv<uuid>", "content": " various tasks", "type": "message"}
```

### 5. Get Thread History

Retrieve the conversation history for a specific thread.

**Endpoint:** `GET /chatbot/thread/{thread_id}/history`

**Response:**
```json
{
  "thread_id": "user123:conv<uuid>",
  "messages": [
    {
      "role": "system",
      "content": "You are Jerry, a helpful customer support chatbot...",
      "type": "SystemMessage"
    },
    {
      "role": "user",
      "content": "Hello Jerry",
      "type": "HumanMessage"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you today?",
      "type": "AIMessage"
    }
  ],
  "count": 3
}
```

### 6. Delete Thread

Delete/reset a conversation thread.

**Endpoint:** `DELETE /chatbot/thread/{thread_id}`

**Response:**
```json
{
  "message": "Thread deleted successfully",
  "thread_id": "user123:conv<uuid>"
}
```

### 7. Execute Tool

Execute a specific tool directly without going through the agent.

**Endpoint:** `POST /chatbot/tool/execute`

**Request Body:**
```json
{
  "tool_name": "send_email",
  "tool_params": {
    "sender_address": "sender@example.com",
    "receiver_address": "recipient@example.com",
    "subject": "Test Email",
    "body": "This is a test email",
    "provider": "google"
  },
  "user_id": "user123",  // Optional
  "thread_id": "user123:conv<uuid>"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "tool": "send_email",
  "result": "Email sent successfully!"
}
```

## Usage Examples

### Example 1: Simple Conversation

```bash
# Create a thread
curl -X POST http://localhost:8010/chatbot/thread/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'

# Send a message
curl -X POST http://localhost:8010/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Hello Jerry!",
    "thread_id": "user123:conv<uuid>"
  }'
```

### Example 2: Send Email via Natural Language

```bash
curl -X POST http://localhost:8010/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Send an email from sender@example.com to recipient@example.com with subject \"Meeting Reminder\" and body \"Don'\''t forget our meeting tomorrow at 10 AM.\""
  }'
```

### Example 3: Execute Tool Directly

```bash
curl -X POST http://localhost:8010/chatbot/tool/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "send_email",
    "tool_params": {
      "sender_address": "sender@example.com",
      "receiver_address": "recipient@example.com",
      "subject": "Test",
      "body": "This is a test",
      "provider": "google"
    }
  }'
```

## Testing

### Automated Tests

Run the automated test suite:

```bash
python /Users/loriscatalano/Progetti/Corretto/Backend/automations/api/test_jerry_api.py
```

### Manual HTTP Tests

Use the provided `.http` file with VS Code REST Client extension:

1. Open `jerry_tests.http` in VS Code
2. Ensure the REST Client extension is installed
3. Click "Send Request" above any test

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (missing required fields)
- `404`: Not Found (thread doesn't exist)
- `500`: Internal Server Error

Error responses include details:

```json
{
  "detail": "Error description here"
}
```

## Thread ID Format

Thread IDs follow the pattern: `user{user_id}:conv{uuid}`

Example: `user123:conv550e8400-e29b-41d4-a716-446655440000`

## Conversation Persistence

- All conversations are persisted in PostgreSQL via LangGraph's PostgresSaver
- Threads maintain full message history including system prompts
- State is automatically checkpointed after each message

## Adding New Tools

To add new tools to Jerry:

1. Create the tool in `automations/chatbot/tools.py`:
```python
@tool
def my_new_tool(param1: str, param2: int) -> str:
    """Tool description here."""
    # Implementation
    return "result"
```

2. Add to the tools list in `services/jerry_service.py`:
```python
tools = [
    send_email,
    my_new_tool,  # Add here
]
```

3. Update the tool mapping in `execute_tool()` method:
```python
available_tools = {
    "send_email": send_email,
    "my_new_tool": my_new_tool,  # Add here
}
```

4. Document in `get_available_tools()` method

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8010/docs`
- ReDoc: `http://localhost:8010/redoc`

## Development

### Project Structure

```
automations/
├── api/
│   ├── main.py                    # FastAPI application
│   ├── controllers/
│   │   └── jerry_controller.py    # Request handling & validation
│   ├── routers/
│   │   └── chatbot.py             # API endpoints
│   ├── services/
│   │   └── jerry_service.py       # Core chatbot logic
│   ├── jerry_tests.http           # Manual HTTP tests
│   └── test_jerry_api.py          # Automated tests
└── chatbot/
    ├── jerry.py                    # Original implementation
    ├── tools.py                    # Available tools
    └── services/
        └── email_service.py        # Email functionality
```

### Best Practices

1. **Always use thread_id**: For multi-turn conversations, always pass the thread_id
2. **Error handling**: Check response status codes and handle errors appropriately
3. **Tool parameters**: Validate tool parameters before calling execute_tool
4. **Streaming**: Use streaming for long responses to improve UX
5. **Thread cleanup**: Delete threads when conversations are complete

## Troubleshooting

### Server won't start
- Check environment variables are set
- Verify PostgreSQL is accessible
- Ensure port 8010 is not in use

### Tool execution fails
- Verify OAuth tokens are configured in database
- Check email service credentials
- Review tool parameters match expected format

### Streaming not working
- Ensure client supports Server-Sent Events
- Check for proxy/firewall issues
- Verify Content-Type headers

## License

Internal use only - Corretto AI Backend

## Support

For issues or questions, contact the development team.
