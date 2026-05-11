# Inkligth
An academic literature reading and translation tool. Upload PDFs, get AI translations, take notes, and generate presentation outlines in one click.

Features
📄 PDF Upload & Management — Drag-and-drop upload with automatic extraction of title, authors, abstract, etc. Folder and tag organization supported.

📖 Dual-pane Reader — Highlight and annotate PDFs on the left, view real-time translations and notes on the right. Adjustable layout with zoom and resizing.

🌐 AI Translation — Select text for instant translation, with support for paragraph and full-text translation. Bring your own API keys for DeepSeek, Qwen, OpenAI, and more.

📝 Note System — Link highlights with paragraph-level notes. Tag notes as innovation points, reusable methods, etc. Aggregate all notes globally.

🤖 AI Analysis — Auto-generate structured summaries, innovation lists, and reproducible method steps.

📊 Group Meeting Prep — One-click generation of presentation outlines, downloadable as .pptx files.

🔍 Semantic Search — Search paper content with natural language using vector embeddings.

📅 Reading Calendar — Track daily reading pages with a heatmap view.

🔐 Privacy & Security — All data accessible only after login; papers stored under personal accounts.

Quick Start
Prerequisites
Node.js 18+

Python 3.11+

PostgreSQL 16+ (pgvector extension required)

Redis (optional, for async tasks)

Backend Setup
bash
cd backend
python -m venv venv
.\venv\Scripts\Activate        # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Copy and edit environment variables
cp .env.example .env
# Fill in your database URL, JWT secret, etc.

# Create database and enable pgvector
psql -U postgres -c "CREATE DATABASE inklight;"
psql -U postgres -d inklight -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Start backend
python -m uvicorn main:app --reload
Frontend Setup
bash
cd frontend
npm install
npm run dev
Visit http://localhost:5173 to get started.

Usage
Sign Up / Login — Create an account first.

Upload Papers — Drag and drop PDF files on the library page; metadata is automatically extracted.

Read & Translate — Enter the reader view, select text to translate instantly, and take notes on the right panel.

Configure AI Engine — Add your own LLM API keys under Settings → AI Engine.

Generate Presentation — Click "Generate Outline" while reading, or manage all outlines from the Group Meeting page.

Project Structure
text
inklight/
├── frontend/          # Vue 3 frontend
│   └── src/
│       ├── views/     # Page components
│       ├── api/       # API layer
│       ├── stores/    # Pinia stores
│       └── components/# Shared components
├── backend/           # FastAPI backend
│   └── app/
│       ├── routers/   # API routes
│       ├── services/  # Business logic
│       ├── models/    # Database models
│       └── core/      # Configuration & security
└── docker-compose.yml # Containerized deployment


