from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END

class ChatbotState(TypedDict):
    messages: List[BaseMessage]
    session_id: str
    pending_confirmation: Optional[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    error_count: int
    memory_context: List[BaseMessage]
