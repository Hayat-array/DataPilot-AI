# DataPilot AI - Backend Foundation (Module 0)

DataPilot AI is a browser-first dataset profiling dashboard backed by a small Flask upload/cache and health API. AI-generated code execution and document ingestion are intentionally disabled until isolated execution and durable indexing services are available.

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
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (bash/macOS/Linux)
source .venv/bin/activate

# Install runtime and development dependencies
pip install -r requirements-dev.txt
```

### 3. Setup Environment Variables

Copy `.env.example` to `.env` and fill out variables:
```bash
cp .env.example .env
```
Configure `MONGO_URI` only when using database-backed features; a Flask `SECRET_KEY` is not required until server-side sessions are added. Temporary server uploads are capped at 4 MiB to stay within serverless request limits; browser-local analysis accepts files up to 16 MiB. Cached uploads are private, expire after one hour, and are not durable or shared across serverless instances. AI-generated Python execution and document ingestion remain disabled until isolated execution and persistent vector-index services are configured; browser-side profiling, filtering, and charts do not require those services.

### 4. Running the application

```bash
python run.py
```

### 5. Running the Tests

```bash
python -m pytest tests/
```
