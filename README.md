# DataPilot AI - Backend Foundation (Module 0)

This is the Flask backend foundation and core infrastructure for **DataPilot AI**, a production-grade autonomous data analysis platform.

## Architecture

The project structure is organized as follows:

```
backend/
├── app/
│   ├── agents/          # Autonomous agents (Planner, Coder, Validator, etc.)
│   ├── auth/            # Authentication (JWT, Roles, Permissions placeholders)
│   ├── config.py        # Environment Configuration classes
│   ├── database/        # Database model declarations
│   ├── extensions.py    # Flask extensions layer (e.g. PyMongo, Redis, Celery)
│   ├── logger.py        # Granular multi-file logging setup
│   ├── middleware/      # Middleware (Request ID, Error handlers)
│   ├── models/          # Persistent collection schema bindings
│   ├── prompts/         # Structured Prompt template repository
│   ├── rag/             # RAG logic (FAISS, Chunkers, Web/PDF loaders)
│   ├── routes/          # Blueprints (Health endpoints, API Routing)
│   ├── schemas/         # Request/Response schema validation bindings
│   ├── services/        # Decoupled business logic services
│   ├── utils/           # Utility helpers (Standard response formats, Validators)
│   └── __init__.py      # Flask Application factory initialization
│
├── tests/               # Testing suite directory
├── uploads/             # Raw user uploaded files
├── outputs/             # Generated plots, CSV, Excel, clean datasets
├── reports/             # Executed analysis reports (PDF, HTML, MD, JSON)
├── generated_code/      # Sandbox and cached execution python scripts
├── logs/                # Logging file outputs
│
├── Dockerfile           # Backend container build script
├── docker-compose.yml   # Multi-service setup (App + MongoDB)
├── requirements.txt     # Dependency requirements file
├── run.py               # Application startup entry point
└── .env.example         # Template settings file
```

## Quick Start

### 1. Requirements

Python 3.12+ (or 3.13) is recommended.

### 2. Setup Virtual Environment

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (bash/macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Environment Variables

Copy `.env.example` to `.env` and fill out variables:
```bash
cp .env.example .env
```
Ensure you have `SECRET_KEY`, `MONGO_URI`, and at least one LLM API key (e.g., `OPENAI_API_KEY`, `GROQ_API_KEY`, or `GOOGLE_API_KEY`).

### 4. Running the application

```bash
python run.py
```

### 5. Running the Tests

```bash
python -m pytest tests/
```
