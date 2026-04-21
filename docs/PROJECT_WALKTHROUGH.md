# JobScope AI — Complete Walkthrough

A full account of what was built, why each decision was made, what went wrong, and how we fixed it. Written as a companion to the top-level [README](../README.md) for anyone who wants the behind-the-scenes detail.

---

## 1. Services and sites used

| What | Why | URL |
|---|---|---|
| **GitHub** | Git hosting, source-of-truth for code | https://github.com/05102005rajat/jobscope-ai |
| **Vercel** | Frontend hosting (React). Auto-deploys from GitHub pushes. | https://jobscope-ai-yov1.vercel.app |
| **Railway** | Backend hosting (FastAPI). Auto-deploys Python from GitHub. | https://jobscope-ai-production.up.railway.app |
| **Supabase** | Managed PostgreSQL. Free tier. We use the Transaction Pooler URL. | supabase.com |
| **Groq** | LLM inference provider — hosts Llama 3.3 70B. Faster and cheaper than OpenAI for this workload. | https://console.groq.com |

---

## 2. Build timeline — what we did, in order

### Phase 1 — Inventory
Started with only a backend skeleton. README promised a Vercel URL that didn't exist. No frontend. Backend had deprecated `@app.on_event`, a fake "agent" that used keyword matching, and a keyword-regex skill extractor with ~80 hardcoded strings.

### Phase 2 — Backend sanity check
Ran `uvicorn app.main:app --port 8000` locally. Verified Supabase was reachable, all CRUD endpoints worked, Groq key was valid. Confirmed `/api/jobs`, `/api/stats`, `/api/chat`, `/api/analyze`, `/api/resume` all responded correctly.

### Phase 3 — Rewrote the agent
The original `graph.py` had keyword routing:
```python
if "interview" in message.lower():
    call_tool("query_applications")
```
This couldn't handle multi-tool questions (e.g. *"give me an overview: total apps, any interviews, what's missing"* needs two tools). Replaced it with a real LangGraph loop using `llm.bind_tools()` and `ToolNode`. Hit a bug: `langgraph-prebuilt` package had its files missing on disk despite pip thinking they were installed. Fixed by `pip install --force-reinstall --no-deps langgraph-prebuilt==1.0.10`.

Then discovered Groq Llama 3.3 occasionally emits malformed tool-call syntax (`<function=query_applications {...}` missing the closing `>` — known Groq quirk). Added a 3-attempt retry loop.

### Phase 4 — Built the React frontend from scratch
Scaffolded with `npm create vite@latest frontend -- --template react`. Installed Tailwind v4, react-router-dom, axios. Built:
- `Layout.jsx` with nav
- `Dashboard.jsx` — stat cards + jobs table
- `AddJob.jsx` — create form
- `Chat.jsx` — agent interface with pre-built prompt chips

### Phase 5 — Inline status editing
Only `delete` existed; no way to change a job's status after creation. Turned the static status pill into a `<select>` with optimistic updates. One click to flip applied → interview.

### Phase 6 — Resume and Analyze pages
Even though the backend had `POST /api/resume` and `POST /api/analyze`, there was no UI for them. Built:
- `Resume.jsx` — drag/drop PDF, shows extracted skills as pills
- `Analyze.jsx` — JD textarea + optional job-link dropdown + colored match score + matched/missing skill pills + suggestions list

### Phase 7 — LLM-based skill extraction
The regex extractor was catching ~44 skills from a real resume and missing specific ones like `C++` (regex broke on `+`), `TF-IDF`, `SimHash`, `Azure AI Foundry`. Replaced `jd_parser.py` with a Groq call that returns a JSON array. Jumped from **44 → 52 skills** with correct casing. Kept the regex as a fallback for when Groq is unreachable.

### Phase 8 — LLM-based semantic matching
Tested a legal-AI JD. Got 43% match. But 2 of 4 "missing" skills (OpenAI, LLM APIs) were things the resume *had* — just phrased differently (Azure OpenAI, LLM, LLM Evaluation). The old code was doing `set(resume_skills) & set(jd_skills)` — exact string intersection — which undermined the whole "AI-powered" pitch.

Created `matcher.py`. One Groq call takes resume skills + JD skills + both texts, and returns `{matched, missing, suggestions}`. Now understands equivalents: `Azure OpenAI` covers `OpenAI`, `LLM` covers `LLM APIs`. **43% → 80% on the same JD.**

Suggestions are grounded in actual resume content:
> "Your Adani RAG chatbot already uses LLMs — rewrite that bullet to explicitly mention 'LLM APIs' and highlight your experience with OpenAI to match the JD."

### Phase 9 — Dashboard UX fixes
Shipped three targeted improvements:
1. "Analyze" button per row → opens `/analyze?job=3` with job pre-selected + JD pre-filled
2. Auto-redirect to Analyze after adding a job with JD text
3. Hint on Avg Match card: *"Run JD Analyzer to populate"*

### Phase 10 — Extractor fix for non-tech JDs
Ran analysis on a Hermeus aerospace intern JD. Got 100% match. Looked wrong. The extractor had pulled out exactly one skill — `"AI"` — scraped from this boilerplate line:
> *"We may use artificial intelligence (AI) tools to support parts of the hiring process"*

With only 1 extracted skill and some LLM stochasticity, score flip-flopped between 0% and 100%. Updated the extractor prompt to:
- **Ignore** EEO / export-control / hiring-AI / salary / benefits sections
- **Include** domain skills (flight testing, aerospace, cross-functional teams) not just tech

After fix: Hermeus JD correctly extracts 7 real requirements and gives a stable **14% match** — accurate signal that a CS student shouldn't apply to an aerospace role.

### Phase 11 — Prepare for GitHub
Discovered `~/.git` (accidental home-dir repo pointing to an old `chatbot_RAG` remote). Initialized a fresh repo inside the project. Verified `.env` was gitignored, `.env.example` was tracked. Rewrote README. Added LICENSE (MIT). Froze `requirements.txt`. Pushed.

### Phase 12 — Deploy
**Railway (backend):**
- Added `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Added `runtime.txt`: `python-3.12`
- Updated CORS in `main.py` to accept `https://.*\.vercel\.app` regex
- Hit: Railway GitHub app didn't have access to the new repo → granted "All repositories" via GitHub App settings
- Hit: Dependency conflict — `langchain-text-splitters==0.2.4` needed old `langchain-core`, but `langchain 1.x` needs new. Removed it (never imported).
- Railway auto-built, assigned domain `jobscope-ai-production.up.railway.app`

**Vercel (frontend):**
- Root directory `frontend`, framework Vite (auto-detected)
- Env var `VITE_API_URL=https://jobscope-ai-production.up.railway.app`
- Deployed to `jobscope-ai-yov1.vercel.app`

**End-to-end verified:** CORS preflight returns 200 with correct `Access-Control-Allow-Origin`. `VITE_API_URL` baked into the bundle. DB rows returned through the full stack.

### Phase 13 — Secret rotation
Rotated Groq key and Supabase password. Hit another gotcha: Supabase's **"Direct connection"** URL is IPv6-only. Railway's runtime is IPv4. Used the **Transaction pooler** URL instead (port 6543, `aws-1-us-east-1.pooler.supabase.com`).

### Phase 14 — Cleanup
Removed stray `~/.git`. Updated README to link the live demo.

---

## 3. File-by-file code walkthrough

### Backend

#### `app/main.py`
FastAPI entry point. Creates the app, attaches CORS middleware (regex for `*.vercel.app` + explicit localhost), mounts 4 routers under `/api`, and runs `init_db()` on startup to auto-create tables via `Base.metadata.create_all`.

#### `app/database.py`
SQLAlchemy setup. Reads `DATABASE_URL` from env, creates engine + session. Declares 3 models:
- **Job** — 13 fields: company, role, status, url, jd_text, location, salary, notes, match_score, missing_skills (JSON string), applied_date, updated_date
- **Resume** — id, filename, raw_text (full PDF text), skills (JSON string), uploaded_date
- **Analysis** — id, job_id, resume_id, match_score, matched_skills, missing_skills, suggestions, created_date

Exports `get_db()` generator for FastAPI's `Depends` injection.

#### `app/models.py`
Pydantic schemas for requests/responses. `JobResponse` explicitly includes `jd_text` so the Analyze page can pre-fill when linking to an existing job.

#### `app/routes/jobs.py`
Standard CRUD (`GET/POST/PUT/DELETE /api/jobs`) plus a `/api/stats` endpoint that computes total, interview rate, response rate, avg match score, and top missing skills (aggregated from all jobs' `missing_skills` JSON).

#### `app/routes/resume.py`
- `POST /api/resume` — accepts multipart PDF, calls PyPDF2 to extract text, calls the LLM extractor, stores.
- `GET /api/resume/latest` — returns the most recent uploaded resume + its skills.

#### `app/routes/analysis.py`
`POST /api/analyze`: fetches latest resume, extracts JD skills, calls the semantic matcher, saves an `Analysis` row, and if `job_id` was passed, updates that job's `match_score` and `missing_skills`. Match score is computed server-side as `matched / (matched + missing) × 100` — not whatever the LLM might return — for determinism.

#### `app/routes/chat.py`
Thin wrapper. `POST /api/chat` → `run_agent(message, db)`. Wraps in try/except to return HTTP 502 (not 500) on agent failure.

#### `app/agent/graph.py`
The most important file in the project.

Builds a LangGraph `StateGraph`:
- `_agent_node` — calls the LLM (with tools bound) on the message history
- `ToolNode(TOOLS)` — prebuilt node that executes any tool calls the LLM emitted
- `_should_continue` — conditional edge: if the last AI message has `tool_calls`, route to `tools`, else END

```
entry → agent → (has tool_calls?) → tools → agent → ... → END
```

`run_agent(message, db)`:
1. Sets DB session in a ContextVar
2. Invokes the graph with the user message + system prompt
3. Retries up to 3x on `tool_use_failed` exceptions (Groq quirk)
4. Returns the last AI message content

#### `app/agent/tools.py`
Four `@tool`-decorated functions with typed signatures:

```python
@tool
def query_applications(status: Optional[str] = None, company: Optional[str] = None, limit: int = 20) -> str:
    db = _db()  # pulled from ContextVar
    ...
```

The `_db_ctx: ContextVar[Session]` is set at request time by `run_agent` and pulled out inside each tool. The LLM never sees a DB argument — only `status`, `company`, `limit` — so the tool schema stays clean.

#### `app/utils/jd_parser.py`
Skill extraction. Primary path is Groq LLM with a detailed system prompt:
- Returns JSON array only, no markdown
- INCLUDES: tech skills, domain skills, hard requirements (STEM enrollment, specific degrees)
- IGNORES: EEO / export-control / hiring-AI / salary / benefits / company mission

Has a `_parse_json_object` helper that's defensive about markdown fences the LLM sometimes adds. Has a regex fallback (30 common skills) if the LLM call fails.

#### `app/utils/matcher.py`
Semantic comparison. One LLM call takes 4 inputs:
- `resume_skills`
- `jd_skills`
- `resume_excerpt` (first 3500 chars — for suggestion grounding)
- `jd_excerpt` (first 3500 chars)

Returns `{matched, missing, suggestions}`. System prompt is explicit about equivalents and bans generic advice. Sanity-checks that every JD skill gets classified (if not, retries). Falls back to case-insensitive set intersection if all retries fail.

#### `app/utils/resume_parser.py`
Trivial 2 functions: `extract_text_from_pdf(content)` via PyPDF2, and `extract_skills(text)` which just delegates to `extract_jd_skills`.

### Frontend

#### `src/App.jsx`
`BrowserRouter` with 5 routes under a shared `Layout`: `/`, `/add`, `/resume`, `/analyze`, `/chat`.

#### `src/api.js`
Axios instance with `baseURL = (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api"`. Exported functions: `listJobs`, `createJob`, `updateJob`, `deleteJob`, `getStats`, `sendChat`, `uploadResume`, `getLatestResume`, `analyzeJD`.

`getLatestResume()` swallows 404s and returns `null` so the UI can distinguish "no resume yet" from "request failed."

#### `src/components/Layout.jsx`
Top nav with 5 `NavLink`s. Active link gets indigo background via NavLink's `isActive` callback.

#### `src/pages/Dashboard.jsx`
Stats grid (4 cards) + jobs table. Status column is a `<select>` with optimistic updates. Each row has `analyze` (link to `/analyze?job=<id>`) and `delete` actions. Shows a yellow banner if no resume uploaded. Avg Match card shows hint text when score is null.

#### `src/pages/AddJob.jsx`
Form with 8 fields. On submit, strips empty strings from payload. If `jd_text` was filled, navigates to `/analyze?job=<created.id>` — otherwise back to `/`. This is the auto-analyze hook.

#### `src/pages/Resume.jsx`
Drag-and-drop zone + click-to-pick-file + file validation (PDF only). Shows current resume filename + uploaded date + skill pills.

#### `src/pages/Analyze.jsx`
Reads `?job=<id>` from the URL via `useSearchParams`. When the jobs list loads, finds the matching job, pre-selects it, and pre-fills the JD textarea from `job.jd_text`.

Shows colored match score (green ≥70%, amber ≥40%, rose <40%), matched/missing skill pills in two columns, suggestions list. Disables the Analyze button if no resume uploaded.

#### `src/pages/Chat.jsx`
Message list + input + Send button + 4 suggestion chips shown only when the conversation is empty. Auto-scrolls to newest message. Error messages render in a rose-tinted bubble.

---

## 4. Every bug we hit and how we fixed it

| # | Bug | Root cause | Fix |
|---|---|---|---|
| 1 | Agent couldn't handle multi-tool questions | Keyword-based routing | Rewrote with `bind_tools` + `ToolNode` |
| 2 | `langgraph.prebuilt` import error | Package files missing despite pip saying installed | `pip install --force-reinstall --no-deps langgraph-prebuilt` |
| 3 | Agent occasionally 500'd | Groq Llama emits malformed `<function=...>` syntax | 3x retry in `run_agent` on `tool_use_failed` |
| 4 | Skill extractor missed C++, TF-IDF, Azure AI Foundry | Regex list + `\b+\b` boundary breaks on `+` | LLM extraction with JSON array output |
| 5 | Match score of 43% on legitimate 80% match | `set.intersection` on exact strings | LLM semantic comparison with equivalence rules |
| 6 | Hermeus JD scored 0% or 100% randomly | Extractor pulled "AI" from EEO boilerplate → 1 skill total | System prompt explicitly ignores EEO / export / hiring-AI / salary sections |
| 7 | Stray `~/.git` at home directory | Accidental `git init` done in `~` earlier | `rm -rf ~/.git` after confirming no commits |
| 8 | Railway couldn't see the GitHub repo | Railway's GitHub App had limited repo access | Granted "All repositories" via GitHub App settings |
| 9 | Railway build failed | `langchain-text-splitters==0.2.4` required `langchain-core<0.3` but langchain 1.x needs `>=1.2` | Removed the unused dep from requirements.txt |
| 10 | Backend crashed after password rotation | Supabase "Direct connection" URL is IPv6-only; Railway is IPv4 | Used Transaction Pooler URL (`pooler.supabase.com`, port 6543) |

---

## 5. Design decisions with real tradeoffs

### Why LLM extraction instead of regex?
- **Regex:** fast, free, deterministic. But brittle — can't handle case variants, compound terms (`Azure AI Foundry`), specialized methods (`SimHash`, `TF-IDF`), or new frameworks. Grows to a 500-line list over time and still misses things.
- **LLM:** ~1s latency, costs fractions of a cent. Handles the long tail correctly. Normalizes casing automatically. Understands context (doesn't extract "AI" from hiring disclaimers).
- **Choice:** LLM, with regex fallback if Groq is unreachable.

### Why LLM comparison instead of embeddings?
- **Embeddings (cosine similarity):** standard RAG move. Cheap once indexed, fast. But gives you a score, not a reason — can't say *"why is this 73% and not 81%?"*
- **LLM comparison:** slower, more expensive. But the same model that classifies can also generate grounded rewrite suggestions — *"rename your Azure OpenAI bullet to match the JD's OpenAI wording"*. That's only possible because the model saw both texts.
- **Choice:** LLM. The suggestion quality is the whole point.

### Why LangGraph instead of vanilla LangChain agents?
- Vanilla `create_tool_calling_agent` is fine for single-turn, but LangGraph's explicit graph makes the flow visible and lets you add conditional edges later (approval gates, retries, branching).
- `ToolNode` handles tool execution + error propagation cleanly.
- **Choice:** LangGraph.

### Why ContextVar for DB injection?
- **Option A — global session singleton:** not safe across concurrent requests.
- **Option B — pass DB through graph state:** leaks into the LLM-visible tool schema; model might try to pass DB args and fail.
- **Option C — ContextVar:** request-scoped, invisible to LLM, zero overhead.
- **Choice:** C.

### Why Groq + Llama over OpenAI?
- **Speed:** Groq serves Llama 3.3 70B at ~500 tok/s — 5-10x faster than OpenAI's equivalents. Matters for chat UI responsiveness.
- **Cost:** free tier covers this project comfortably.
- **Tradeoff:** Llama 3.3 emits malformed tool calls occasionally. We work around with retries.

### Why `*.vercel.app` CORS regex?
Every Vercel preview deployment gets a different subdomain. Hardcoding origins means every PR preview needs a backend config change. Regex allows any Vercel URL automatically.

---

## 6. Notable numbers

| Metric | Value |
|---|---|
| Files in repo | 45+ |
| Frontend pages | 5 |
| Backend routes | 10 endpoints across 4 routers |
| LLM calls per "Analyze" | 2 (extract JD + semantic match) |
| Agent tools | 4 (query, stats, analysis, suggestions) |
| Skill extraction jump | 44 regex → 52 LLM |
| Match score fix (legal-AI JD) | 43% → 80% |
| Hermeus match after extractor fix | 100%/0% coin-flip → stable 14% |
| Groq retry attempts | 3 |

---

## 7. What's honest about the limits

- The agent is **single-turn** — it doesn't remember your last message. Adding conversational memory would be ~20 lines using LangGraph's checkpointer + a `thread_id`.
- Resume skill extraction is **one-shot** — no chunking, no RAG over the resume. Works because resumes are short (~3000 tokens). Wouldn't scale to full-length work samples.
- Match scoring is **deterministic from the LLM's classification** (`matched / (matched + missing)`). Two runs of the same JD can produce slightly different skill lists and thus slightly different scores. For a resume tool, this is fine; for a rank-stable leaderboard, it wouldn't be.

## 8. If you had another weekend

1. **FAISS semantic search over resume bullets** — so the analyzer can say *"Your Adani bullet on line 3 is the closest existing evidence for this JD's LLM requirement"*, not just "you have LLM experience somewhere."
2. **Thread-scoped chat memory** via LangGraph checkpointer — so the agent remembers earlier messages.
3. **Auth** — right now everyone sees the same demo DB. A 50-line `fastapi-users` setup would gate data per-user.
4. **LLM skill extraction caching** — same JD pasted twice calls the LLM twice. A simple SHA of the text → cached skill list in Postgres would cut cost/latency on repeat views.
