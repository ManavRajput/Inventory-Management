from app.Agents.State.state import  ChatbotState
from app.Agents.Nodes.chat import WRITE_TOOLS
from langchain_core.messages import HumanMessage

def should_execute_tools(state: ChatbotState) -> str:
    """Decide if tools should be executed"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    
    if not tool_calls:
        return "final_response"
    
    # Check if any write tools need confirmation
    write_tools = [tc for tc in tool_calls if tc["name"] in WRITE_TOOLS]
    if write_tools and not state.get("pending_confirmation", {}).get("confirmed", False):
        return "confirmation"
    
    return "execute_tools"

def should_handle_errors(state: ChatbotState) -> str:
    """Check if errors need handling"""
    tool_results = state.get("tool_results", [])
    has_errors = any(not r.get("success", True) for r in tool_results)
    
    if has_errors:
        return "error_handling"
    return "llm_continue"

def check_confirmation_response(state: ChatbotState) -> str:
    """Check if user confirmed or denied write operation"""
    if not state.get("pending_confirmation"):
        return "llm"
    
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage):
        content = last_message.content.lower()
        if any(word in content for word in ["yes", "confirm", "ok", "proceed"]):
            return "execute_write_tools"
        elif any(word in content for word in ["no", "cancel", "stop", "abort"]):
            return "cancel_operation"
    
    return "ask_confirmation_again"
