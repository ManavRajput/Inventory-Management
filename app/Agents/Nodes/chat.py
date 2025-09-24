from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.Agents.tools.tools import get_price, get_stock, get_card, varieties, search, sell_multiple_items,sell_single_item,compute_order_total
from app.Agents.Graph.prompts import inventory_chain
from app.Agents.Graph.memory_manager import memory_manager
from app.Agents.State.state import  ChatbotState
import json

# Available tools mapping
# In your graph.py or wherever you define TOOLS
TOOLS = {
    "get_price": get_price,
    "get_stock": get_stock, 
    "get_card": get_card,
    "varieties": varieties,
    "search": search,
    "sell_single_item": sell_single_item,           # NEW
    "sell_multiple_items": sell_multiple_items,     # NEW  
    "compute_order_total": compute_order_total      # NEW
}

# Update tool categories
SAFE_TOOLS = {"get_price", "get_stock", "get_card", "varieties", "search", "compute_order_total"}
WRITE_TOOLS = {"sell_single_item", "sell_multiple_items"}  # These need confirmation


async def memory_node(state: ChatbotState) -> ChatbotState:
    """Load conversation memory for the session"""
    session_id = state.get("session_id", "default")
    memory = memory_manager.get_memory(session_id)
    
    # Get conversation history
    chat_history = memory.chat_memory.messages
    
    return {
        **state,
        "memory_context": chat_history
    }

async def llm_node(state: ChatbotState) -> ChatbotState:
    """Main LLM reasoning node with tool calling"""
    # Prepare input for LLM
    chain_input = {
        "chat_history": state.get("memory_context", []),
        "messages": state["messages"]
    }
    
    # Get LLM response with potential tool calls
    response = await inventory_chain.ainvoke(chain_input)
    
    # Add AI response to messages
    updated_messages = state["messages"] + [response]
    
    return {
        **state,
        "messages": updated_messages
    }

async def tool_execution_node(state: ChatbotState) -> ChatbotState:
    """Execute safe tools and collect results"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    
    tool_results = []
    tool_messages = []
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in SAFE_TOOLS:
            try:
                # Execute the tool
                tool_func = TOOLS[tool_name]
                result = await tool_func.ainvoke(tool_args)
                
                # Create tool message
                tool_message = ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                    "success": True
                })
                
            except Exception as e:
                # Handle tool errors
                error_message = ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(error_message)
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "error": str(e),
                    "success": False
                })
    
    return {
        **state,
        "messages": state["messages"] + tool_messages,
        "tool_results": tool_results
    }

async def confirmation_node(state: ChatbotState) -> ChatbotState:
    """Handle confirmation requests for write operations"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    
    # Check if any write tools are being called
    write_tool_calls = [tc for tc in tool_calls if tc["name"] in WRITE_TOOLS]
    
    if write_tool_calls:
        # Store pending confirmation
        pending = {
            "tool_calls": write_tool_calls,
            "requires_confirmation": True
        }
        
        # Create confirmation request message
        confirmation_msg = AIMessage(
            content="⚠️ This action will modify your inventory/place an order. Please confirm by saying 'yes' or 'confirm'."
        )
        
        return {
            **state,
            "messages": state["messages"] + [confirmation_msg],
            "pending_confirmation": pending
        }
    
    return state

async def error_handling_node(state: ChatbotState) -> ChatbotState:
    """Handle errors and suggest alternatives"""
    tool_results = state.get("tool_results", [])
    failed_tools = [r for r in tool_results if not r.get("success", True)]
    
    if failed_tools:
        error_messages = []
        for failed_tool in failed_tools:
            tool_name = failed_tool["tool"]
            error = failed_tool.get("error", "Unknown error")
            
            if "not found" in error.lower():
                suggestion = "Let me search for similar products. Try describing the item differently."
            elif "insufficient stock" in error.lower():
                suggestion = "This item has limited stock. Would you like to check available quantity?"
            else:
                suggestion = "Please try again or contact support if the issue persists."
            
            error_msg = f"❌ {tool_name} failed: {error}\n💡 {suggestion}"
            error_messages.append(error_msg)
        
        # Create error response
        error_response = AIMessage(content="\n\n".join(error_messages))
        
        return {
            **state,
            "messages": state["messages"] + [error_response],
            "error_count": state.get("error_count", 0) + 1
        }
    
    return state

async def final_response_node(state: ChatbotState) -> ChatbotState:
    """Generate final response and save to memory"""
    # Get the last user input and AI response
    user_input = None
    ai_response = None
    
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and ai_response is None:
            ai_response = msg.content
        elif isinstance(msg, HumanMessage) and user_input is None:
            user_input = msg.content
            break
    
    # Save to memory
    if user_input and ai_response:
        session_id = state.get("session_id", "default")
        memory = memory_manager.get_memory(session_id)
        memory.save_context(
            {"input": user_input},
            {"output": ai_response}
        )
    
    return state
