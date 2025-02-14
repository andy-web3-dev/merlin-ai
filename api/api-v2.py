from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from chatbot import (
    create_graph,
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create the agent graph once
graph = create_graph()

class ChatRequestMessage(BaseModel):
    role: str
    content: str
    chatId: int
    createdAt: str

class ChatRequest(BaseModel):
    model: str
    messages: list[ChatRequestMessage]

@app.post("/api/chat")
async def api_chat(request_data: ChatRequest):
    """
    REST API endpoint for interacting with the agent, with streaming response.
    """
    # Extract messages from request data
    messages = request_data.messages
    if not messages:
        raise HTTPException(status_code=422, detail="Missing messages")

    # Create state with messages
    state = {"messages": [
        {
            "role": "system",
            "content": (
                "You are a knowledgeable assistant about the Movement network "
                "and its ecosystem. You can retrieve context from a vector store "
                "whenever needed. Answer truthfully; if unsure, say so. Don't "
                "answer questions that's not about blockchain."
                'When user ask you to do a swap action, you should response this snippet code to help render a swap widget: <iframe src="https://app.mosaic.ag/swap/{from}-{to}?amount={amountIn}"></iframe>. The {from}, {to} and {amountIn} variables are optional, if user don\'t provide them, just skip. Please don\'t nest the tag inside code tag'
            )
        }
    ]}

    # Convert message objects to appropriate format
    for msg in messages:
        if msg.role == 'system':
            state["messages"].append(SystemMessage(msg.content))
        elif msg.role == "user":
            state["messages"].append(HumanMessage(msg.content))
        elif msg.role == "assistant":
            state["messages"].append(AIMessage(msg.content))

    print("[INFO] API chat request received")

    async def generate_streaming_response():
        for stream_mode, data in graph.stream(state, stream_mode=["messages", "values"]):
            if stream_mode == "messages":
                if data and isinstance(data[0], AIMessage):
                    token = {
                        "model": request_data.model,
                        "created_at": datetime.now().isoformat() + "Z",
                        "message": {
                            "role": "assistant",
                            "content": data[0].content,
                        },
                        "done": False
                    }
                    yield json.dumps(token) + "\n"
            elif isinstance(data, dict):
                state.update(data)

        # Send final done message
        token = {
            "model": request_data.model,
            "created_at": datetime.now().isoformat() + "Z",
            "message": {
                "role": "assistant",
                "content": "",
            },
            "done": True,
            "done_reason": "stop"
        }
        yield json.dumps(token) + "\n"

    return StreamingResponse(generate_streaming_response(), media_type="application/x-ndjson")
