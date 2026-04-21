from contextvars import ContextVar
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Analysis, Job
import json


_db_ctx: ContextVar[Session] = ContextVar("jobscope_db_session")


def set_db_session(db: Session) -> object:
    return _db_ctx.set(db)


def reset_db_session(token) -> None:
    _db_ctx.reset(token)


def _db() -> Session:
    return _db_ctx.get()


@tool
def query_applications(
    status: Optional[str] = None,
    company: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Search the user's job applications.

    Args:
        status: Filter by status. One of: applied, interview, offer, rejected.
        company: Case-insensitive substring match on company name.
        limit: Max results (default 20).
    """
    db = _db()
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status.lower())
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    jobs = query.order_by(Job.applied_date.desc()).limit(limit).all()
    if not jobs:
        return "No applications found matching those filters."

    rows = [
        f"- {j.company} | {j.role} | {j.status} | applied {j.applied_date:%Y-%m-%d}"
        f" | match {j.match_score if j.match_score is not None else 'N/A'}"
        for j in jobs
    ]
    return f"Found {len(jobs)} applications:\n" + "\n".join(rows)


@tool
def get_statistics() -> str:
    """Return overall application metrics: total count, breakdown by status,
    interview rate, response rate, average match score, and top missing skills."""
    db = _db()
    total = db.query(Job).count()
    if total == 0:
        return "No applications tracked yet."

    status_counts = dict(
        db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    )
    interviews = status_counts.get("interview", 0) + status_counts.get("offer", 0)
    pending = status_counts.get("applied", 0)
    avg_score = (
        db.query(func.avg(Job.match_score))
        .filter(Job.match_score.isnot(None))
        .scalar()
    )

    skill_counts: dict[str, int] = {}
    rows = db.query(Job.missing_skills).filter(Job.missing_skills.isnot(None)).all()
    for (skills_json,) in rows:
        try:
            for s in json.loads(skills_json):
                skill_counts[s] = skill_counts.get(s, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue
    top_missing = sorted(skill_counts, key=skill_counts.get, reverse=True)[:5]

    return (
        f"Total: {total} | Pending: {pending} | Interviews: {interviews} "
        f"| Rejections: {status_counts.get('rejected', 0)} | Offers: {status_counts.get('offer', 0)}\n"
        f"Interview rate: {interviews / total * 100:.1f}% | "
        f"Response rate: {(total - pending) / total * 100:.1f}%\n"
        f"Avg match score: {f'{avg_score:.1f}%' if avg_score else 'N/A'}\n"
        f"Top missing skills: {', '.join(top_missing) if top_missing else 'N/A'}"
    )


@tool
def get_latest_analysis() -> str:
    """Return the most recent JD-vs-resume analysis (match score, matched/missing skills)."""
    db = _db()
    analysis = db.query(Analysis).order_by(Analysis.created_date.desc()).first()
    if not analysis:
        return "No analyses yet. Use the JD Analyzer to compare a JD against your resume."

    matched = json.loads(analysis.matched_skills) if analysis.matched_skills else []
    missing = json.loads(analysis.missing_skills) if analysis.missing_skills else []
    return (
        f"Match score: {analysis.match_score}%\n"
        f"Matched ({len(matched)}): {', '.join(matched[:10])}\n"
        f"Missing ({len(missing)}): {', '.join(missing[:10])}"
    )


@tool
def get_improvement_suggestions() -> str:
    """Aggregate improvement suggestions across the user's 5 most recent JD analyses."""
    db = _db()
    analyses = db.query(Analysis).order_by(Analysis.created_date.desc()).limit(5).all()
    if not analyses:
        return "No analyses yet. Analyze a few JDs first to get suggestions."

    missing: set[str] = set()
    suggestions: list[str] = []
    for a in analyses:
        if a.missing_skills:
            missing.update(json.loads(a.missing_skills))
        if a.suggestions:
            suggestions.extend(json.loads(a.suggestions))

    return (
        f"Based on {len(analyses)} recent analyses.\n"
        f"Most commonly missing skills: {', '.join(list(missing)[:10]) or 'none'}\n"
        f"Recommendations:\n"
        + "\n".join(f"  - {s}" for s in list(dict.fromkeys(suggestions))[:5])
    )


TOOLS = [
    query_applications,
    get_statistics,
    get_latest_analysis,
    get_improvement_suggestions,
]
