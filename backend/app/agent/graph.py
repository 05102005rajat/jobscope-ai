import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.tools import TOOLS, reset_db_session, set_db_session

load_dotenv()


SYSTEM_PROMPT = """You are JobScope AI, an assistant that helps the user track and \
optimize their job applications.

You have tools for reading the user's application database, statistics, and JD-vs-resume \
analyses. Call a tool whenever the user's question needs real data — do not guess numbers \
or invent applications. After calling tools, answer concisely with specific figures and \
names from the tool output. If the user asks something no tool can answer, say so plainly.
"""


_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY"),
).bind_tools(TOOLS)


def _agent_node(state: MessagesState) -> dict:
    return {"messages": [_llm.invoke(state["messages"])]}


def _should_continue(state: MessagesState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


_workflow = StateGraph(MessagesState)
_workflow.add_node("agent", _agent_node)
_workflow.add_node("tools", ToolNode(TOOLS))
_workflow.set_entry_point("agent")
_workflow.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
_workflow.add_edge("tools", "agent")

graph = _workflow.compile()


def run_agent(message: str, db) -> str:
    """Run one turn of the agent. Injects the DB session via ContextVar so the tools
    can reach it without leaking the session through the LLM-visible tool args."""
    inputs = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
    }

    token = set_db_session(db)
    try:
        # Groq's Llama 3.3 occasionally emits malformed tool-call syntax
        # (tool_use_failed). Retrying usually clears it.
        last_err: Exception | None = None
        for _ in range(3):
            try:
                result = graph.invoke(inputs)
                last_err = None
                break
            except Exception as e:
                last_err = e
                if "tool_use_failed" in str(e):
                    continue
                raise
        if last_err is not None:
            raise last_err
    finally:
        reset_db_session(token)

    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return "I could not process your request. Please try again."
