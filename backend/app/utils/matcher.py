"""Semantic skill-matching and suggestion generation via Groq.

Compares a resume's skills against a JD's skills, recognizing equivalents
("Azure OpenAI" covers "OpenAI"; "LLM" covers "LLM APIs"), and generates
concrete rewrite/add suggestions grounded in the actual resume text.
Falls back to exact case-insensitive set comparison if the LLM call fails.
"""

import json
import logging
import os
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


_SYSTEM = """You compare a candidate's resume against a job description.

For each JD skill, decide whether the resume covers it:
- MATCHED: the resume has the skill directly OR a clearly equivalent /
  broader / specific-instance-of skill. Be generous about equivalents —
  tools in the same category count. Examples of valid coverage:
    "Azure OpenAI" / "Groq" / "OpenAI SDK"      covers "LLM APIs"
    "Git" / "GitHub"                             covers "Version Control"
    "Python" / "Java" / "C++" / "C#"             covers "OOP" / "Object-Oriented Programming"
    "RESTful API endpoints" + backend work       covers "Backend System Integration"
    "Azure OpenAI"                               covers "OpenAI"
    "LLM" / "Large Language Models"              covers "LLM APIs"
    "PostgreSQL" / "MySQL"                       covers "SQL"
    "React" / "Vue" / "Angular"                  covers "modern JS framework"
    "RPA workflows" / "n8n" / "Zapier"           covers "workflow automation" / "automation tools"
    "FastAPI" / "Flask" / "Express"              covers "REST APIs" / "building APIs"
    "Docker" + "CI/CD" + cloud deploy            covers "deployed applications"
    a CS degree in progress                      covers "Computer Science" / "CS degree"

- ALTERNATIVE / "ANY ONE OF" skills: if the JD skill is a combined entry
  like "C# / Python / Java (any one)" or "OpenAI / Anthropic / similar",
  it is MATCHED when the resume covers ANY ONE of the listed options.
  Do not require all of them.

- MISSING: the resume doesn't cover it, even loosely, and no reasonable
  equivalent is present.

Be reasonably generous on equivalents but do NOT invent coverage that
isn't somewhere in the resume.

Return ONLY a JSON object (no prose, no markdown):
{
  "matched":  ["<JD skill>", ...],
  "missing":  ["<JD skill>", ...],
  "suggestions": ["<concrete suggestion>", ...]
}

Every JD skill must appear in exactly one of "matched" or "missing".
Use the EXACT JD skill string when listing it.

Suggestions must be:
- SPECIFIC: reference real phrases from the resume and the JD
- ACTIONABLE: say what to add, rewrite, or reframe
- 3 to 5 bullets, highest-impact first
- Focus on closing truly-missing gaps first, then on terminology alignment
- Do NOT suggest rewrites for skills you already marked as matched.

Bad: "Add more keywords."
Good: "Your Adani RAG chatbot already calls LLM APIs — rewrite that bullet
       to use the phrase 'LLM APIs (OpenAI, local)' to directly match the JD."
Good: "No OCR experience shown. Add a small OCR project using Tesseract
       or AWS Textract — this is a hard requirement in the JD."
"""


_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY"),
)

# Used only after a parse/validation failure on the first attempt. A blind
# identical retry at temperature 0 tends to reproduce the same malformed or
# incomplete output, so the retry nudges the temperature up slightly to force
# a genuinely different sample.
_llm_retry = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY"),
)

_RETRY_NUDGE = (
    "That response was not a valid JSON object, or it did not classify every "
    "JD skill as matched or missing. Reply again with ONLY a JSON object of "
    'the form {"matched": [...], "missing": [...], "suggestions": [...]} '
    "covering every JD skill exactly once."
)


def _parse_json_object(raw: str) -> dict | None:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def _fallback(resume_skills: list[str], jd_skills: list[str]) -> dict:
    r_lower = {s.lower() for s in resume_skills}
    matched = [j for j in jd_skills if j.lower() in r_lower]
    missing = [j for j in jd_skills if j.lower() not in r_lower]
    return {"matched": matched, "missing": missing, "suggestions": []}


def compare(
    resume_skills: list[str],
    jd_skills: list[str],
    resume_text: str = "",
    jd_text: str = "",
) -> dict:
    """Compare resume vs JD using an LLM.

    Returns {matched, missing, suggestions}. Falls back to exact set
    comparison (no suggestions) if the LLM call fails.
    """
    if not jd_skills:
        return {"matched": [], "missing": [], "suggestions": []}

    payload = {
        "resume_skills": resume_skills,
        "jd_skills": jd_skills,
        "resume_excerpt": (resume_text or "")[:3500],
        "jd_excerpt": (jd_text or "")[:3500],
    }

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=json.dumps(payload)),
    ]
    llm = _llm
    for attempt in range(3):
        try:
            resp = llm.invoke(messages)
        except Exception as exc:
            logger.warning("matcher: Groq call failed on attempt %d: %s", attempt + 1, exc)
            llm = _llm_retry
            continue

        data = _parse_json_object(resp.content)
        if data:
            matched = [s for s in data.get("matched", []) if isinstance(s, str)]
            missing = [s for s in data.get("missing", []) if isinstance(s, str)]
            suggestions = [s for s in data.get("suggestions", []) if isinstance(s, str)]

            # Sanity check: every JD skill classified exactly once
            classified = {s.lower() for s in matched} | {s.lower() for s in missing}
            if {s.lower() for s in jd_skills}.issubset(classified):
                return {
                    "matched": matched,
                    "missing": missing,
                    "suggestions": suggestions,
                }
            logger.warning(
                "matcher: response left JD skills unclassified on attempt %d", attempt + 1
            )
        else:
            logger.warning(
                "matcher: unparseable LLM response on attempt %d: %r",
                attempt + 1,
                resp.content[:300],
            )

        # Re-ask instead of blindly resending the identical prompt, and switch
        # to a slightly higher temperature so the retry isn't just
        # re-sampling the same broken/incomplete output.
        messages = messages + [
            AIMessage(content=resp.content),
            HumanMessage(content=_RETRY_NUDGE),
        ]
        llm = _llm_retry

    logger.warning("matcher: all Groq attempts failed, falling back to exact set comparison")
    return _fallback(resume_skills, jd_skills)
