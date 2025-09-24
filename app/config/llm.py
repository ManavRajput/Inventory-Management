from langchain_google_genai import ChatGoogleGenerativeAI
from app.Agents.tools.tools import get_card,get_price,get_stock,varieties,search

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

tools = [get_price, get_stock, get_card, varieties, search]
llm_with_tools = llm.bind_tools(tools)

# # Example
# response = llm_with_tools.invoke("What is the price of product TSHIRT-BLK-M?")
# print(response)
# print("Tool calls:", response.tool_calls)

