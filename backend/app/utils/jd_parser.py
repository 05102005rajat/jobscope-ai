"""Skill extraction from resume / JD text.

Primary path: Groq LLM returns a normalized JSON array of skills.
Fallback path: regex match against a small built-in list (used only if the LLM
call fails — keeps the app functional if Groq is unreachable).
"""

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq


_SYSTEM = """You extract real, relevant skills and requirements from resume or \
job-description text.

Return ONLY a JSON array of strings. No prose, no markdown fences, no keys.

INCLUDE:
- Technical skills: programming languages, frameworks, libraries, databases,
  cloud services, ML/AI concepts (RAG, agents, fine-tuning), tools, protocols,
  notable methods (TF-IDF, SimHash, SGP4, MCMC, etc.).
- Domain skills and hard requirements: "flight testing", "aircraft systems",
  "orbital mechanics", "GAAP", "clinical trials", "FDA regulation",
  "CAD design", "finite-element analysis", "cross-functional teamwork",
  "financial modeling", "supply chain" — anything the job actually needs done.
- Degree or enrollment requirements if explicitly stated as a bar
  (e.g. "STEM program enrollment", "BS in Computer Science").

IGNORE:
- EEO / equal-opportunity / non-discrimination statements.
- Export-control / ITAR / citizenship disclaimers.
- "We use AI tools in hiring" or applicant-tracking / privacy disclaimers.
  These often say "AI" in boilerplate — DO NOT extract "AI" from them.
- Salary ranges, benefits lists, location, employment type.
- Company descriptions and mission statements.
- Soft skills like "strong communicator", "passionate", "team player"
  unless the JD explicitly frames them as a concrete requirement (e.g.
  "excellent written communication" stays out; "experience presenting
  technical findings to executives" counts).

Normalize casing ("PostgreSQL", "FastAPI", "LangGraph", "C++"). Deduplicate.
Do not invent skills that are not in the text.
"""

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY"),
)


def _parse_json_array(raw: str) -> list[str] | None:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        # Occasionally the model adds a leading sentence before the array.
        m = re.search(r"\[.*\]", s, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, list):
        return None
    return [x.strip() for x in data if isinstance(x, str) and x.strip()]


def _extract_with_llm(text: str) -> list[str] | None:
    for _ in range(2):
        try:
            resp = _llm.invoke(
                [
                    SystemMessage(content=_SYSTEM),
                    HumanMessage(content=text[:12000]),
                ]
            )
            skills = _parse_json_array(resp.content)
            if skills is not None:
                # Dedupe case-insensitively but preserve the LLM's preferred casing
                seen: dict[str, str] = {}
                for s in skills:
                    key = s.lower()
                    if key not in seen:
                        seen[key] = s
                return list(seen.values())
        except Exception:
            continue
    return None


_FALLBACK_PATTERNS = [
    "python", "java", "javascript", "typescript", r"c\+\+", "c#", "ruby", "go",
    "rust", "kotlin", "swift", "scala", "sql", "bash", "html", "css",
    "react", "angular", "vue", r"next\.js", r"node\.js", "express", "django",
    "flask", "fastapi", "spring", "tailwind",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "matplotlib",
    "langchain", "langgraph", "openai", "rag", "faiss", "transformers",
    "postgresql", "mysql", "mongodb", "redis", "supabase",
    "aws", "azure", "gcp", "docker", "kubernetes", "vercel", "railway",
    "git", "github", "linux", "unix", "jupyter",
    "rest api", "graphql", "ci/cd",
]


def _extract_with_regex(text: str) -> list[str]:
    text_l = text.lower()
    found = []
    for pattern in _FALLBACK_PATTERNS:
        if re.search(r"\b" + pattern + r"\b", text_l):
            skill = pattern.replace(r"\+", "+").replace(r"\.", ".")
            found.append(skill)
    return sorted(set(found))


def extract_jd_skills(text: str) -> list[str]:
    """Extract technical skills. Uses Groq; falls back to regex on LLM failure."""
    if not text or not text.strip():
        return []
    llm_result = _extract_with_llm(text)
    if llm_result is not None:
        return llm_result
    return _extract_with_regex(text)
