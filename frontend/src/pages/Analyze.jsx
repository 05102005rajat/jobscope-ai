import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { analyzeJD, getLatestResume, listJobs } from "../api";

function ScoreRing({ score }) {
  const pct = Math.max(0, Math.min(100, score));
  const color =
    pct >= 70 ? "text-emerald-400" : pct >= 40 ? "text-amber-400" : "text-rose-400";
  return (
    <div className={`text-5xl font-semibold ${color}`}>
      {pct.toFixed(0)}
      <span className="text-2xl text-slate-500">%</span>
    </div>
  );
}

export default function Analyze() {
  const [searchParams] = useSearchParams();
  const preselectJobId = searchParams.get("job") || "";

  const [resume, setResume] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [jdText, setJdText] = useState("");
  const [jobId, setJobId] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    getLatestResume().then(setResume);
    listJobs().then((js) => {
      setJobs(js);
      if (preselectJobId) {
        const job = js.find((j) => String(j.id) === preselectJobId);
        if (job) {
          setJobId(String(job.id));
          if (job.jd_text) setJdText(job.jd_text);
        }
      }
    });
  }, [preselectJobId]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!jdText.trim()) return;
    setErr("");
    setResult(null);
    setRunning(true);
    try {
      const res = await analyzeJD({
        jd_text: jdText,
        job_id: jobId ? Number(jobId) : undefined,
      });
      setResult(res);
    } catch (e2) {
      setErr(e2.response?.data?.detail || e2.message || "Analysis failed");
    } finally {
      setRunning(false);
    }
  };

  const inputCls =
    "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">JD Analyzer</h1>
        <p className="text-sm text-slate-400">
          Paste a job description — we extract its required skills with an LLM,
          compare to your resume, and flag the gaps.
        </p>
      </div>

      {!resume && (
        <div className="rounded-md border border-amber-700 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
          No resume uploaded yet.{" "}
          <a href="/resume" className="underline hover:text-amber-100">
            Upload one
          </a>{" "}
          before running analysis.
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm text-slate-300">
            Link to an existing application (optional)
          </label>
          <select
            className={inputCls}
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
          >
            <option value="">— none —</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.company} — {j.role}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">
            If linked, the job's match score and missing skills get updated.
          </p>
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-300">Job description</label>
          <textarea
            required
            rows={12}
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste the full job description here…"
            className={inputCls}
          />
        </div>

        {err && <div className="text-sm text-rose-400">{err}</div>}

        <button
          type="submit"
          disabled={running || !resume}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {running ? "Analyzing…" : "Analyze"}
        </button>
      </form>

      {result && (
        <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center gap-6">
            <ScoreRing score={result.match_score} />
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">
                Match score
              </div>
              <div className="mt-1 text-sm text-slate-300">
                {result.matched_skills.length} matched ·{" "}
                {result.missing_skills.length} missing
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-xs uppercase tracking-wide text-emerald-400">
                Matched skills ({result.matched_skills.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {result.matched_skills.length === 0 ? (
                  <span className="text-sm text-slate-500">none</span>
                ) : (
                  result.matched_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-300 ring-1 ring-emerald-500/40"
                    >
                      {s}
                    </span>
                  ))
                )}
              </div>
            </div>
            <div>
              <div className="mb-2 text-xs uppercase tracking-wide text-rose-400">
                Missing from resume ({result.missing_skills.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {result.missing_skills.length === 0 ? (
                  <span className="text-sm text-slate-500">none</span>
                ) : (
                  result.missing_skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-rose-500/15 px-2.5 py-1 text-xs text-rose-300 ring-1 ring-rose-500/40"
                    >
                      {s}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          {result.suggestions.length > 0 && (
            <div>
              <div className="mb-2 text-xs uppercase tracking-wide text-slate-400">
                Suggestions
              </div>
              <ul className="space-y-1 text-sm text-slate-300">
                {result.suggestions.map((s, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-slate-500">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
