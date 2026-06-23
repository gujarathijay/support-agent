# Support Agent

AI-powered multi-agent system for customer support triage and resolution, built with FastAPI, LangGraph, and Claude.

## Overview

A support ticket comes in, and three agents work it in sequence:

1. **Triage** — classifies category, priority, and sentiment
2. **Research** — looks up relevant context (tools, knowledge base, prior tickets)
3. **Resolution** — drafts a response for human approval

Every run is traced (span-by-span) and tickets move through a simple approve/reject workflow before a response goes out.

## Tech Stack

- **Backend:** FastAPI, LangGraph, LangChain, Anthropic Claude
- **Frontend:** React, TypeScript, Vite
- **Evals:** Braintrust
- **Storage:** SQLite (tickets), Chroma (vector store)

## Project Structure

```
backend/
  app/
    agents/        # triage, research, resolution agent nodes
    tools/         # tools available to agents
    graph.py       # LangGraph workflow wiring
    main.py        # FastAPI app & routes
    config.py      # environment-driven settings
    tracing.py     # trace/span recording
    memory.py      # long-term memory storage
    ticket_store.py
    database.py
  evals/           # eval dataset, scorers, Braintrust runner
frontend/
  src/             # React app
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```
ANTHROPIC_API_KEY=your-key-here
BRAINTRUST_API_KEY=your-key-here   # optional, for evals
```

Run the API:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/triage` | Single-agent triage |
| POST | `/resolve` | Full workflow → pending approval |
| GET | `/tickets` | List tickets (filter by status) |
| GET | `/tickets/{id}` | Get a single ticket |
| POST | `/tickets/{id}/approve` | Approve a pending ticket |
| POST | `/tickets/{id}/reject` | Reject a pending ticket |
| GET | `/traces` | List recent traces |
| GET | `/traces/{id}` | Get a single trace |

## Evals

```bash
cd backend
python evals/run_evals.py            # logs to Braintrust if BRAINTRUST_API_KEY is set
python evals/run_evals.py --local    # prints results to terminal only
```
