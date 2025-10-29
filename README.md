Here’s a professional and clear **README.md** file for your project:

---

# 🏪 Inventory Management System (AI-Powered for Kirana Shops)

This repository contains the **Inventory Management System** powered by **Agentic AI**, designed to help small **Kirana shops** automate and streamline their inventory management, order handling, and customer interaction.

The system includes:

* A **RESTful API** backend to handle inventory operations.
* An **AI-powered Telegram bot** (`@Inventory_021`) that understands natural language queries and performs all tasks — from checking stock to placing and managing orders.

---

## 🚀 Features

* 🤖 **Agentic AI Integration:** Automatically updates and manages inventory in real-time.
* 💬 **Telegram Bot Interface:** Allows shopkeepers and customers to interact with the system via natural language.
* 🛒 **Order Management:** Create, update, and track orders seamlessly.
* 📦 **Inventory Tracking:** Manage stock levels, product categories, and pricing with minimal manual input.
* 🌐 **API Endpoints:** Ready-to-use endpoints for building web or mobile interfaces.

---

## 🧠 How It Works

1. The **API** handles all CRUD operations for products, orders, and users.
2. The **Telegram Bot** connects with the API and translates natural language queries into actions.
3. **Agentic AI** continuously analyzes inventory trends and updates stock details automatically.

---

## 🧩 Project Structure

```
|-- Docs
|-- api
    |-- extra.py
    |-- main.py
|-- app
    |-- Agents
        |-- Graph
            |-- memory_manager.py
            |-- prompts.py
        |-- Nodes
            |-- chat.py
            |-- condition.py
        |-- State
            |-- state.py
        |-- graph.py
        |-- tools
            |-- tools.py
    |-- DB
        |-- Sql
            |-- db_manager.py
        |-- models
            |-- schema.py
        |-- repositories
            |-- inventory_repo.py
        |-- services
            |-- inventory_service.py
    |-- config
        |-- llm.py
    |-- telegram
        |-- bot.py
|-- offline.db

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ManavRajput/Inventory-Management.git
cd Inventory-Management
```

### 2. Create a Virtual Environment and Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # On Linux / macOS
venv\Scripts\activate      # On Windows
pip install -r requirements.txt
```

---

## 🧾 Running the API Server

Start the backend API to handle inventory operations:

```bash
uvicorn api.main:app --reload
```

By default, the server runs at:
➡️ `http://127.0.0.1:5000/`

You can use tools like **Postman** or **cURL** to test the endpoints.

---

## 💬 Running the Telegram Bot

After starting the API, launch the Telegram bot to interact with the system.

```bash
python -m app.telegram.bot
```

Once the bot is running, go to Telegram and open **[@Inventory_021](https://t.me/Inventory_021)** to start chatting!

---

## 🧪 Example Commands for the Bot

* `/start` – Begin interaction with the bot.
* “Are onion available in the shop” – View inventory.
* “Create an order for sugar and oil” – Place a customer order.
* “Check the availability of shampoo” – Get alerts on items running out.

---

## 🔐 Environment Variables

Create a `.env` file in the project root and set the following:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
API_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///inventory.db
GOOGLE_API_KEY = google_key
```

---

## 🧰 Tech Stack

* **Python 3.10+**
* **Flask / FastAPI** (for API)
* **SQLite / PostgreSQL** (for database)
* **Python-Telegram-Bot** (for Telegram integration)
* **OpenAI / LangChain** (for Agentic AI functionality)

---

## 🧑‍💻 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

---

## 📞 Contact

* **Telegram Bot:** [@Inventory_021](https://t.me/Inventory_021)
* **Maintainer:** Manav Pathania
* **Email:** manavpathania780@gmail.com

---
