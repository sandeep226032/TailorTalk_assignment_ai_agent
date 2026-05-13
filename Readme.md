# 🗂️ TailorTalk Drive Agent

A conversational AI agent that searches your Google Drive files using natural language. Built with FastAPI, LangChain, and Streamlit.

## 🏗️ Architecture

```
┌─────────────────────┐        ┌──────────────────────┐        ┌─────────────────────┐
│                     │  HTTP  │                      │  Tool  │                     │
│  Streamlit Frontend │ ──────▶│     FastAPI Backend  │ ──────▶│  Google Drive API   │
│  (Chat UI)          │        │  + LangChain Agent   │        │  (files.list)       │
│                     │◀────── │  + Groq LLM          │◀────── │                     │
└─────────────────────┘        └──────────────────────┘        └─────────────────────┘
```

## ✨ Features

- **Natural Language Search**: "Find my project proposal from last week" or "Show all PDFs about sales".
- **Intelligent Memory**: Maintains context across the conversation.
- **Robust Tooling**: Uses Google Drive API with advanced query building.
- **Fast Reasoning**: Powered by Llama 3 on Groq for sub-second responses.

---

## 🚀 Setup Guide (Local Development)

### 1. Prerequisites
- Python 3.10+
- Google Cloud Project with Drive API enabled
- Service Account with `credentials.json`
- Groq API Key

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:
```env
GROQ_API_KEY=your_key_here
DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_CREDENTIALS_PATH=credentials.json
ALLOWED_ORIGINS=http://localhost:8501
```

Run the server:
```bash
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Deployment Guide

### Backend (Railway)
1.  Connect your repo to Railway.
2.  Set the Root Directory to `backend/`.
3.  **Environment Variables**:
    - `GROQ_API_KEY`: Your key.
    - `DRIVE_FOLDER_ID`: Your folder ID.
    - `GOOGLE_CREDENTIALS_JSON`: Paste the ENTIRE content of your `credentials.json` file.
    - `ALLOWED_ORIGINS`: Your Streamlit Cloud URL.
4.  **Networking**: Set Port to `8000`.

### Frontend (Streamlit Cloud)
1.  Connect your repo to Streamlit Cloud.
2.  Set Main file path to `frontend/app.py`.
3.  **Advanced Settings (Secrets)**:
    ```toml
    BACKEND_URL = "https://your-railway-app.up.railway.app"
    ```

---

## 📁 Project Structure

```
tailortalk-drive-agent/
├── backend/
│   ├── api/            # Route handlers and routers
│   ├── core/           # Config, constants, and logging
│   ├── services/       # Business logic (Agent & Chat)
│   ├── tools/          # Google Drive search tools
│   └── main.py         # Entry point
├── frontend/
│   ├── components/     # UI elements
│   ├── services/       # API client logic
│   └── app.py          # Streamlit UI
└── README.md
```
