# api.py
import uuid
import threading
from queue import Queue, Empty

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse

# Import your agent and related classes/functions from chatbot.py.
from chatbot import (
    create_graph,
    HumanMessage,
    AIMessage,
)

app = FastAPI()

# Create the agent graph once.
graph = create_graph()

# In-memory session store: mapping session_id -> conversation state.
session_store = {}

@app.post("/start_session")
async def start_session():
    """
    Start a new conversation session with initial system context.
    """
    session_id = str(uuid.uuid4())
    state = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable assistant about the Movement network "
                    "and its ecosystem. You can retrieve context from a vector store "
                    "whenever needed. Answer truthfully; if unsure, say so. Don't "
                    "answer questions that's not about blockchain."
                )
            }
        ]
    }
    session_store[session_id] = state
    print(f"[INFO] New session started: {session_id}")
    return {"session_id": session_id}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for interacting with the agent.
    User messages are added to the session state and then the agent's response
    is streamed token-by-token.
    """
    if session_id not in session_store:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    state = session_store[session_id]
    print(f"[INFO] WebSocket connected for session: {session_id}")

    try:
        while True:
            # Wait for a user message.
            user_input = await websocket.receive_text()
            print(f"[INFO] Received from user (session {session_id}): {user_input}")
            if user_input.strip().lower() in ["bye", "quit", "exit"]:
                await websocket.send_text("Session ended. Bye!")
                print(f"[INFO] Session {session_id} ended by user command.")
                break

            # Append user message to session state.
            state["messages"].append(HumanMessage(user_input))

            # Create a queue to stream tokens.
            token_queue = Queue()

            def token_generator():
                """
                Runs in a background thread to push agent tokens to a queue.
                """
                # Iterate over the tokens from the agent's stream.
                for stream_mode, data in graph.stream(state, stream_mode=["messages", "values"]):
                    if stream_mode == "messages":
                        if data and isinstance(data[0], AIMessage):
                            token_queue.put(data[0].content)
                    else:
                        state.update(data)
                # When streaming is complete, push an end marker.
                token_queue.put("[[END_OF_RESPONSE]]")

            # Start token streaming in a background thread.
            thread = threading.Thread(target=token_generator, daemon=True)
            thread.start()

            # Stream tokens from the queue to the WebSocket.
            while True:
                try:
                    token = token_queue.get(timeout=1.0)
                except Empty:
                    continue
                if token == "[[END_OF_RESPONSE]]":
                    # Send the marker to the client so it knows the response ended.
                    await websocket.send_text(token)
                    break
                print(f"[INFO] Sending token to user (session {session_id}): {token}")
                await websocket.send_text(token)
    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected for session: {session_id}")

@app.post("/end_session/{session_id}")
async def end_session(session_id: str):
    """
    End a session by deleting its stored state.
    """
    if session_id in session_store:
        del session_store[session_id]
        print(f"[INFO] Session ended and cleaned up: {session_id}")
        return {"message": f"Session {session_id} ended."}
    raise HTTPException(status_code=404, detail="Session not found.")

# --- HTML/JS UI ---
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>AI Agent Chat</title>
        <style>
            body { font-family: Arial, sans-serif; }
            #chatLog { 
                border: 1px solid #ccc; 
                height: 300px; 
                overflow-y: scroll; 
                padding: 10px; 
                white-space: pre-wrap; 
                background-color: #f9f9f9;
            }
            .user { color: blue; margin-bottom: 5px; }
            .chatbot { color: green; margin-bottom: 10px; }
            #controls { margin-top: 10px; }
            #startSessionBtn { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Chat with the AI Agent</h1>
        <div>
            <button id="startSessionBtn">Start Session</button>
            <span id="sessionStatus"></span>
        </div>
        <div id="chatLog"></div>
        <div id="controls">
            <input type="text" id="userInput" size="80" placeholder="Type your message here..." disabled />
            <button id="sendBtn" disabled>Send</button>
        </div>
        <script>
            let sessionId = null;
            let ws = null;
            let currentResponseElement = null;
            const startSessionBtn = document.getElementById("startSessionBtn");
            const sessionStatus = document.getElementById("sessionStatus");
            const chatLog = document.getElementById("chatLog");
            const userInput = document.getElementById("userInput");
            const sendBtn = document.getElementById("sendBtn");

            // Start session by calling the API.
            startSessionBtn.addEventListener("click", async () => {
                try {
                    const response = await fetch("/start_session", { method: "POST" });
                    const data = await response.json();
                    sessionId = data.session_id;
                    sessionStatus.textContent = "Session ID: " + sessionId;
                    console.log("Session started with ID:", sessionId);
                    // Enable the message input and send button.
                    userInput.disabled = false;
                    sendBtn.disabled = false;
                    // Connect to the WebSocket.
                    connectWebSocket();
                } catch (error) {
                    console.error("Error starting session:", error);
                }
            });

            // Establish the WebSocket connection.
            function connectWebSocket() {
                ws = new WebSocket("ws://" + location.host + "/ws/" + sessionId);
                ws.onopen = () => {
                    console.log("WebSocket connected for session:", sessionId);
                };
                ws.onmessage = (event) => {
                    console.log("Received from chatbot:", event.data);
                    // If the end-of-response marker is received, finalize the message.
                    if (event.data === "[[END_OF_RESPONSE]]") {
                        if (currentResponseElement) {
                            // Append two line breaks to finalize the chatbot response.
                            currentResponseElement.innerHTML += "<br><br>";
                        }
                        currentResponseElement = null;
                    } else {
                        // If no chatbot message is being built, create one.
                        if (currentResponseElement === null) {
                            currentResponseElement = document.createElement("div");
                            currentResponseElement.classList.add("chatbot");
                            currentResponseElement.innerHTML = "Merlin: " + event.data;
                            chatLog.appendChild(currentResponseElement);
                        } else {
                            // Append the token to the current chatbot message.
                            currentResponseElement.innerHTML += event.data;
                        }
                    }
                    chatLog.scrollTop = chatLog.scrollHeight;
                };
                ws.onclose = () => {
                    console.log("WebSocket closed for session:", sessionId);
                };
            }

            // Send message on button click.
            sendBtn.addEventListener("click", () => {
                const message = userInput.value.trim();
                if (message === "" || !ws || ws.readyState !== WebSocket.OPEN) return;
                console.log("Sending message from user:", message);
                // Append user message with one newline.
                const userMessageElement = document.createElement("div");
                userMessageElement.classList.add("user");
                userMessageElement.innerHTML = "King Arthur's servant: " + message + "<br>";
                chatLog.appendChild(userMessageElement);
                chatLog.scrollTop = chatLog.scrollHeight;
                ws.send(message);
                // Clear the input box.
                userInput.value = "";
            });

            // Allow "Enter" key to send message.
            userInput.addEventListener("keyup", function(event) {
                if (event.key === "Enter") {
                    sendBtn.click();
                }
            });
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    """
    Serve a simple HTML page that provides the chat UI.
    """
    return HTMLResponse(html)
