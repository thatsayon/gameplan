import os
import json
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from collections import defaultdict
 
# --- LangChain imports ---------------------------------------------------
from langchain_google_genai import ChatGoogleGenerativeAI          # Gemini
from langchain_tavily import TavilySearch                          # Search tool
from langchain.memory import ConversationBufferMemory
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
 
# --- Load environment variables ----------------------------------------
load_dotenv()                     # GOOGLE_API_KEY & TAVILY_API_KEY
 
# --- Initialize Gemini model (tool-use ready) --------------------------
MODEL_ID = "gemini-2.5-flash"      # or "gemini-1.5-flash-latest"
llm = ChatGoogleGenerativeAI(
    model=MODEL_ID,
    temperature=0.7,
    convert_system_message_to_instructions=True  # Gemini best-practice
)
 
# --- Define Tavily tool -------------------------------------------------
search_tool = TavilySearch(max_results=5)   # schema: {"query": str}
tools = [search_tool]
 
# --- Bind tool schema to the model --------------------------------------
llm = llm.bind_tools(tools)                 # <-- absolutely required
 
# --- File-based storage for memory ------------------------------------
MEMORY_STORAGE_DIR = "user_memory"
os.makedirs(MEMORY_STORAGE_DIR, exist_ok=True)
 
def get_user_memory(session_id: str) -> ConversationBufferMemory:
    """
    Retrieve the user's memory from file storage using the session_id.
    If the file doesn't exist, it returns a new ConversationBufferMemory instance.
    """
    memory_file = os.path.join(MEMORY_STORAGE_DIR, f"{session_id}.json")
    if os.path.exists(memory_file):
        with open(memory_file, "r") as f:
            history = json.load(f)
            memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            memory.chat_history = history  # Load history from file
            return memory
    return ConversationBufferMemory(memory_key="chat_history", return_messages=True)
 
def save_user_memory(session_id: str, memory: ConversationBufferMemory):
    """
    Save the user's memory to a file, ensuring each session's data is isolated.
    """
    memory_file = os.path.join(MEMORY_STORAGE_DIR, f"{session_id}.json")
    with open(memory_file, "w") as f:
        json.dump(memory.chat_history, f)
 
# --- Create the prompt ---------------------------------------------------
SYSTEM = (
    "You are SportMate, a helpful sport assistant.\n"
    "Whenever the user asks for live, recent or latest scores or news, "
    "call the `tavily_search` tool with **one** argument: `query`.\n"
    "After the JSON returns, summarise the result in a sentence.\n"
    "For all other questions, answer normally and remember preferences."
)
 
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    MessagesPlaceholder("chat_history", optional=True),
    ("user", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])
 
# --- Build the agent -----------------------------------------------------
core_agent = create_openai_tools_agent(llm, tools, prompt)   # generic helper
agent = AgentExecutor(agent=core_agent, tools=tools,
                      memory=None, verbose=True)  # Memory will be dynamic
 
# --- FastAPI Integration -------------------------------------------------
app = FastAPI()
 
class UserMessage(BaseModel):
    message: str
    session_id: str  # Added session ID to link chat history
    user_id: int
    access_token: str
 
@app.post("/chat")
async def chat_with_bot(user_message: UserMessage):
    headers = {
        "Authorization": f"Bearer {user_message.access_token}"
    }
 
    # Use session-specific memory from file
    memory = get_user_memory(user_message.session_id)
 
    # 🔁 Get history from Django (authenticated)
    chat_history_response = requests.get(
        f"http://127.0.0.1:8000/c/chat-history/{user_message.session_id}/",
        headers=headers
    )
 
    if chat_history_response.status_code == 200:
        chat_history = chat_history_response.json()
        history = [entry["user_message"] for entry in chat_history]
        history.append(user_message.message)
    else:
        history = [user_message.message]
 
    # 🔁 Get user info from the about endpoint
    about_response = requests.get(
        "http://127.0.0.1:8000/auth/about/",
        headers=headers
    )
 
    if about_response.status_code == 200:
        about_info = about_response.json()
        favorite_sport = about_info.get("favorite_sport", "")
        details = about_info.get("details", "")
    else:
        favorite_sport = "Unknown"
        details = "No details available"
 
    # Combine user message with additional user info for a richer AI input
    full_input = f"{user_message.message}\nFavorite Sport: {favorite_sport}\nDetails: {details}"
 
    # 💬 Generate Gemini response
    response = agent.invoke({"input": full_input})
 
    # Save updated memory back to file
    memory.chat_history = history
    save_user_memory(user_message.session_id, memory)
 
    # 🔁 Save message to Django (authenticated)
    requests.post(
        "http://127.0.0.1:8000/chat/history/",
        json={
            "message": user_message.message,
            "session_id": user_message.session_id,
            "user": user_message.user_id
        },
        headers=headers
    )
 
    return {"response": response["output"]}
 
# --- Run FastAPI with Uvicorn -------------------------------------------
# To run this FastAPI app, use the following command in terminal:
# uvicorn main:app --reload
# Make sure to replace 'main' with the name of your Python file (without the extension)
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)