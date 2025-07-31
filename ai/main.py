import os
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

# ---------------------------------------------------------------------
# 0.  Load secrets / config
# ---------------------------------------------------------------------
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DJANGO_BASE = os.getenv("DJANGO_BASE", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------
# 1.  Build GLOBAL, stateless pieces once at import time
# ---------------------------------------------------------------------
MODEL_ID = "gemini-2.5-flash"
llm = ChatGoogleGenerativeAI(
    model=MODEL_ID,
    temperature=0.7,
    convert_system_message_to_instructions=True,
)

search_tool = TavilySearch(max_results=5)
tools = [search_tool]
llm = llm.bind_tools(tools)

SYSTEM_MESSAGE = (
    "You are SportMate, a helpful sport assistant.\n"
    "Whenever the user asks for live, recent or latest scores or news, "
    "call the `tavily_search` tool with **one** argument: `query`.\n"
    "After the JSON returns, summarise the result in a sentence.\n"
    "For all other questions, answer normally and remember preferences."
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_MESSAGE),
        MessagesPlaceholder("chat_history", optional=True),
        ("user", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

BASE_CHAIN = create_openai_tools_agent(llm, tools, prompt)

# ---------------------------------------------------------------------
# 2.  Factory: build per-session AgentExecutor
# ---------------------------------------------------------------------

async def fetch_chat_history(session_id: str, token: str) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_BASE}/c/chat-history/{session_id}/",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch chat history from Django API.")
        return response.json()


async def _build_agent(session_id: str, access_token: str) -> AgentExecutor:
    chat_history_data = await fetch_chat_history(session_id, access_token)

    history = ChatMessageHistory()
    for item in chat_history_data:
        history.add_user_message(item["user_message"])
        history.add_ai_message(item["bot_message"])

    memory = ConversationBufferMemory(
        chat_memory=history,
        return_messages=True,
    )

    return AgentExecutor(
        agent=BASE_CHAIN,
        tools=tools,
        memory=memory,
        verbose=False,
        handle_parsing_errors=True,
    )


# ---------------------------------------------------------------------
# 3.  FastAPI plumbing
# ---------------------------------------------------------------------
app = FastAPI()
client = httpx.AsyncClient(timeout=10)

class UserMessage(BaseModel):
    message: str
    session_id: str
    user_id: int
    access_token: str

class ChatResponse(BaseModel):
    response: str

# Helpers -------------------------------------------------------------
async def _django_get(path: str, token: str) -> httpx.Response:
    return await client.get(
        f"{DJANGO_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )

async def _django_post(path: str, token: str, data: dict) -> None:
    await client.post(
        f"{DJANGO_BASE}{path}",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )

# Endpoint -------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(payload: UserMessage) -> ChatResponse:
    # Build session-specific agent
    agent = await _build_agent(payload.session_id, payload.access_token)

    # -- Enrich prompt with user profile --------------------------------
    try:
        about_resp = await _django_get("/auth/about/", payload.access_token)
        about_json = about_resp.json() if about_resp.status_code == 200 else {}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Django profile fetch failed: {e}")

    favorite = about_json.get("favorite_sport", "Unknown")
    details = about_json.get("details", "No details available")

    full_input = (
        f"{payload.message}\n"
        f"Favorite Sport: {favorite}\n"
        f"Details: {details}"
    )

    # -- Invoke the agent -----------------------------------------------
    try:
        result = agent.invoke({"input": full_input})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # -- Mirror message to Django (fire-and-forget) ---------------------
    try:
        await _django_post(
            "/chat/history/",
            payload.access_token,
            {
                "message": payload.message,
                "session_id": payload.session_id,
                "user": payload.user_id,
            },
        )
    except httpx.HTTPError:
        pass  # don't block the user if logging fails

    return ChatResponse(response=result["output"])
