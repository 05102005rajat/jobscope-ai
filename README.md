# JobScope AI

AI-powered job application tracker with a LangGraph agent. Track applications, upload your resume, paste a job description, and get a semantic match score plus concrete resume-improvement suggestions — all grounded in an LLM that can reason over your actual pipeline.

**Tech stack:** React · Vite · Tailwind v4 · FastAPI · SQLAlchemy · PostgreSQL (Supabase) · LangGraph · LangChain · Groq (Llama 3.3 70B)

---

## Features

- **Application CRUD.** Track company, role, status, URL, salary, notes, and JD text. Inline status dropdown updates the row without a page reload.
- **Dashboard metrics.** Total applications, interview rate, response rate, average match score — all computed live from the database.
- **Resume ingestion.** Drag a PDF in; PyPDF2 extracts the text and a Groq LLM returns a normalized list of skills (handles specifics like `TF-IDF`, `SimHash`, `Azure AI Foundry` that a keyword matcher would miss).
- **JD analysis.** Paste any job description. The same extractor normalizes requirements, ignoring EEO / export-control / hiring-AI boilerplate. A second LLM call does *semantic* skill comparison — `Azure OpenAI` counts as coverage for `OpenAI`, `LLM` counts for `LLM APIs` — and generates concrete, resume-specific rewrite suggestions.
- **LangGraph chat agent.** Natural-language questions like *"what's my interview rate?"* or *"any apps at Google?"* route through a real `bind_tools` + `ToolNode` loop: the LLM chooses which of four tools to call, the tool hits the database, the loop closes when the LLM stops requesting tools. Handles multi-tool turns in a single response.
- **Tight loop:** add a job with a JD pasted → you land on Analyze with it pre-filled → run analysis → match score appears on the Dashboard row.

## Architecture

```
┌──────────────────────────────────────────────────┐
│  React + Vite + Tailwind (frontend/)             │
│  Dashboard · Add Job · Resume · Analyze · Chat   │
└─────────────────────┬────────────────────────────┘
                      │ axios → /api
                      ▼
┌──────────────────────────────────────────────────┐
│  FastAPI (backend/app)                           │
│    routes/jobs.py        CRUD + stats            │
│    routes/resume.py      PDF upload + parse      │
│    routes/analysis.py    JD-vs-resume compare    │
│    routes/chat.py        → LangGraph agent       │
│                                                   │
│  agent/graph.py    bind_tools + ToolNode loop    │
│  agent/tools.py    4 tools w/ typed args,        │
│                    DB session via ContextVar     │
│                                                   │
│  utils/jd_parser.py   LLM skill extraction       │
│  utils/matcher.py     LLM semantic comparison    │
│  utils/resume_parser.py   PyPDF2 text extract    │
└─────────────────────┬────────────────────────────┘
                      │ SQLAlchemy
                      ▼
              PostgreSQL (Supabase)
              jobs · resumes · analyses
```

## Agent design notes

- **Real tool-calling, not keyword routing.** [backend/app/agent/graph.py](backend/app/agent/graph.py) binds tools via LangChain's `bind_tools` and runs a standard `agent → ToolNode → agent` loop with a conditional edge that checks `tool_calls` on the last message.
- **DB session injection.** Tools need a SQLAlchemy session but the LLM must not see it. The session is stashed in a `ContextVar` at request time and pulled out inside each tool body — see [tools.py](backend/app/agent/tools.py). Tool signatures stay clean (`status: str | None`, `company: str | None`) so the model can call them with proper args.
- **Groq tool-call reliability.** Llama 3.3 on Groq occasionally emits malformed tool-call syntax (`tool_use_failed`). The agent retries up to 3 times before surfacing a 502 — see the retry loop in `run_agent`.

## Running locally

### Prerequisites
- Python 3.10+
- Node 18+
- A Groq API key ([console.groq.com](https://console.groq.com))
- A PostgreSQL instance (Supabase free tier is fine)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL and GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
```

Tables auto-create on first request via `Base.metadata.create_all`.

### Frontend

```bash
cd frontend
npm install

# If your backend is not on http://localhost:8000, set it:
echo "VITE_API_URL=http://localhost:8000" > .env

npm run dev
# Opens at http://localhost:5173
```

## API

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/api/jobs`           | List applications |
| `POST`   | `/api/jobs`           | Create application |
| `PUT`    | `/api/jobs/{id}`      | Update (supports partial — e.g. `{"status": "interview"}`) |
| `DELETE` | `/api/jobs/{id}`      | Delete |
| `GET`    | `/api/stats`          | Total, interview rate, response rate, avg match, top missing skills |
| `POST`   | `/api/resume`         | Upload PDF (multipart). Returns extracted skills. |
| `GET`    | `/api/resume/latest`  | Latest uploaded resume + skills |
| `POST`   | `/api/analyze`        | `{ jd_text, job_id? }` → match score, matched/missing skills, suggestions |
| `POST`   | `/api/chat`           | `{ message }` → agent response |

## Layout

```
backend/
  app/
    main.py              FastAPI app + CORS
    database.py          SQLAlchemy models (Job, Resume, Analysis)
    models.py            Pydantic request/response schemas
    routes/              jobs · resume · analysis · chat
    agent/               graph.py · tools.py
    utils/               jd_parser · matcher · resume_parser
  requirements.txt
  .env.example

frontend/
  src/
    api.js               axios client
    App.jsx              router
    components/Layout.jsx
    pages/               Dashboard · AddJob · Resume · Analyze · Chat
  package.json
  vite.config.js
```

## Status

Frontend and backend work end-to-end locally against Supabase + Groq. Not yet deployed to Vercel/Railway.

## License

MIT — see [LICENSE](LICENSE).
