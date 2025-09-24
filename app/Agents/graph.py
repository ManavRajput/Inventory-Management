from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.Agents.State.state import ChatbotState
from app.Agents.Nodes.chat import memory_node,llm_node,tool_execution_node,confirmation_node,error_handling_node,final_response_node
from app.Agents.Nodes.condition import should_execute_tools,should_handle_errors,check_confirmation_response

def create_chatbot_graph():
    """Create the main chatbot graph"""
    
    # Create the graph
    workflow = StateGraph(ChatbotState)
    
    # Add nodes
    workflow.add_node("memory", memory_node)
    workflow.add_node("llm", llm_node)
    workflow.add_node("execute_tools", tool_execution_node)
    workflow.add_node("confirmation", confirmation_node)
    workflow.add_node("error_handling", error_handling_node)
    workflow.add_node("final_response", final_response_node)
    
    # Set entry point
    workflow.set_entry_point("memory")
    
    # Add edges
    workflow.add_edge("memory", "llm")
    
    # Conditional edges from LLM
    workflow.add_conditional_edges(
        "llm",
        should_execute_tools,
        {
            "execute_tools": "execute_tools",
            "confirmation": "confirmation", 
            "final_response": "final_response"
        }
    )
    
    # From tool execution, check for errors
    workflow.add_conditional_edges(
        "execute_tools",
        should_handle_errors,
        {
            "error_handling": "error_handling",
            "llm_continue": "llm"
        }
    )
    
    # From confirmation, check user response
    workflow.add_conditional_edges(
        "confirmation",
        check_confirmation_response,
        {
            "execute_write_tools": "execute_tools",
            "cancel_operation": "final_response",
            "ask_confirmation_again": "confirmation"
        }
    )
    
    # Terminal edges
    workflow.add_edge("error_handling", "llm")
    workflow.add_edge("final_response", END)
    
    return workflow.compile()

# Create the compiled graph
chatbot_graph = create_chatbot_graph()
