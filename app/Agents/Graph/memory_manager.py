from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage
from typing import List
from app.Agents.Graph.prompts import inventory_chain, inventory_chain


# Create conversation memory
def create_conversation_memory() -> ConversationBufferMemory:
    """Create a conversation buffer memory instance"""
    return ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        input_key="input",
        output_key="output"
    )

# Session-based memory storage (for multiple users)
class MemoryManager:
    def __init__(self):
        self.sessions = {}
    
    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create memory for a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = create_conversation_memory()
        return self.sessions[session_id]
    
    def clear_memory(self, session_id: str):
        """Clear memory for a session"""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
    
    def delete_session(self, session_id: str):
        """Delete a session completely"""
        if session_id in self.sessions:
            del self.sessions[session_id]

# Global memory manager instance
memory_manager = MemoryManager()

# Helper function to format conversation with memory
async def get_conversation_context(session_id: str) -> List[BaseMessage]:
    """Get conversation history for a session"""
    memory = memory_manager.get_memory(session_id)
    return memory.chat_memory.messages

# Usage example function
async def process_with_memory(session_id: str, user_input):
    """Process user input with conversation memory"""
    # Get conversation history
    memory = memory_manager.get_memory(session_id)
    chat_history = memory.chat_memory.messages
    
    # Create the input for the chain
    chain_input = {
        "chat_history": chat_history,
        "messages": [("human", user_input)]
    }
    # Get response from the chain
    response = await inventory_chain.ainvoke(chain_input)
    
    # Save to memory
    memory.save_context(
        {"input": user_input},
        {"output": response.content}
    )
    
    return response



# Optional: Memory with sliding window (keeps only last N exchanges)
def create_windowed_memory(k: int = 10) -> ConversationBufferMemory:
    """Create memory that keeps only the last k exchanges"""
    from langchain.memory import ConversationBufferWindowMemory
    return ConversationBufferWindowMemory(
        k=k,
        memory_key="chat_history",
        return_messages=True,
        input_key="input",
        output_key="output"
    )
