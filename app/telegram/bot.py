
from app.Agents.graph import chatbot_graph 
from app.Agents.Graph import memory_manager

from app.DB.Sql.db_manager import AsyncDBManager



import asyncio
import logging
from typing import Dict, Any
import os
import signal
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatAction
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage


load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TelegramInventoryBot:
    def __init__(self):
        self.db_manager = None
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.application = None
        self.is_running = False
    
    async def initialize(self):
        """Initialize database and components"""
        try:
            self.db_manager = AsyncDBManager()
            await self.db_manager.open()
            await self.db_manager.init_schema()
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean shutdown"""
        logger.info("🧹 Cleaning up...")
        if self.db_manager:
            await self.db_manager.close()
            logger.info("Database connection closed")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram application stopped")
    
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        # Initialize session
        self.active_sessions[user_id] = {
            "session_id": f"telegram_{user_id}",
            "user_name": user_name,
            "started_at": asyncio.get_event_loop().time()
        }
        
        welcome_text = f"""
🛒 **Welcome {user_name}!**

I'm your **InventoryBot** - here to help with:

✅ **Check availability** - "Do you have black M t-shirt?"
💰 **Get prices** - "What's the price of 3 t-shirts?" 
🔍 **Search products** - "Find cotton shirts"
📦 **Place orders** - "I want 2 black M t-shirts"
🧮 **Calculate totals** - "Total for my order?"

Just type your question naturally!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search", callback_data="action_search"),
                InlineKeyboardButton("📊 Check Stock", callback_data="action_stock")
            ],
            [
                InlineKeyboardButton("💰 Prices", callback_data="action_price"),
                InlineKeyboardButton("❓ Help", callback_data="action_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **InventoryBot Commands**

**Commands:**
• `/start` - Start the bot
• `/help` - Show help
• `/clear` - Clear memory
• `/status` - Bot status

**Examples:**
• "Do you have TSHIRT-BLK-M?"
• "Price of 5 white L t-shirts?"
• "I want to order 2 items"
• "Search for cotton products"

Just type naturally - I understand context!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def clear_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation memory"""
        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}"
        memory_manager.clear_memory(session_id)
        
        await update.message.reply_text("🧹 Memory cleared! Starting fresh.")
    
    async def status_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check system status"""
        try:
            # Test DB
            if self.db_manager:
                result = await self.db_manager.execute_query("SELECT 1 as test")
                db_status = "✅ Connected" if result else "❌ Error"
            else:
                db_status = "❌ Not initialized"
            
            status = f"""
📊 **System Status**
🗄️ Database: {db_status}
👥 Active Users: {len(self.active_sessions)}
🤖 Bot: ✅ Running
            """
            await update.message.reply_text(status, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Status error: {str(e)}")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        responses = {
            "action_search": "🔍 **Search Products**\n\nType: 'Find cotton t-shirts' or 'Search for shoes'",
            "action_stock": "📊 **Check Stock**\n\nAsk: 'Do you have TSHIRT-BLK-M?' or 'Is white L available?'",
            "action_price": "💰 **Get Prices**\n\nAsk: 'Price of black M t-shirt?' or 'Cost of 3 items?'",
            "action_help": "❓ **Help**\n\nJust type naturally:\n• Questions about products\n• Order requests\n• Price inquiries\n\nI'll understand!"
        }
        
        response = responses.get(query.data, "🤖 Try typing your question!")
        await query.edit_message_text(response, parse_mode='Markdown')
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages using the graph"""
        user_id = update.effective_user.id
        user_input = update.message.text
        session_id = f"telegram_{user_id}"
        
        # Check session
        if user_id not in self.active_sessions:
            await update.message.reply_text("👋 Please use /start first!")
            return
        
        try:
            # Show typing
            await update.message.reply_chat_action(ChatAction.TYPING)
            
            # Prepare state for graph
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "session_id": session_id,
                "pending_confirmation": None,
                "tool_results": [],
                "error_count": 0,
                "memory_context": []
            }
            
            # Use your compiled graph
            final_state = await chatbot_graph.ainvoke(initial_state)
            
            # Extract response
            response = "Sorry, I couldn't process that."
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, AIMessage):
                    response = msg.content
                    break
            
            # Handle long messages
            if len(response) > 4000:
                parts = [response[i:i+3900] for i in range(0, len(response), 3900)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(part)
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=part
                        )
            else:
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            await update.message.reply_text(
                "❌ Something went wrong. Please try again."
            )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler"""
        logger.error(f"Exception while handling update: {context.error}")
    
    def setup_handlers(self):
        """Setup all handlers"""
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("help", self.help_handler))
        self.application.add_handler(CommandHandler("clear", self.clear_handler))
        self.application.add_handler(CommandHandler("status", self.status_handler))
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
        self.application.add_error_handler(self.error_handler)
    
    async def start(self):
        """Start the bot"""
        if not TELEGRAM_TOKEN:
            raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        
        try:
            # Initialize components
            await self.initialize()
            
            # Create application
            self.application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Setup handlers
            self.setup_handlers()
            
            # Initialize application
            await self.application.initialize()
            
            logger.info("🚀 Starting Telegram bot...")
            print("🤖 InventoryBot is running!")
            print("📱 Go to Telegram and send /start")
            print("Press Ctrl+C to stop")
            
            # Start polling
            self.is_running = True
            await self.application.start()
            
            # Run until stopped
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def stop(self):
        """Stop the bot"""
        logger.info("🛑 Stopping bot...")
        self.is_running = False

# Global bot instance
bot_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    if bot_instance:
        asyncio.create_task(bot_instance.stop())

async def main():
    """Main function with proper cleanup"""
    global bot_instance
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot_instance = TelegramInventoryBot()
    
    try:
        await bot_instance.start()
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        print("👋 Bot stopped cleanly")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        sys.exit(1)
