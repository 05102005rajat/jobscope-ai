import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteJob, getLatestResume, getStats, listJobs, updateJob } from "../api";

const STATUSES = ["applied", "interview", "offer", "rejected"];

const STATUS_STYLES = {
  applied: "bg-slate-700 text-slate-200",
  interview: "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40",
  offer: "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40",
  rejected: "bg-rose-500/20 text-rose-300 ring-1 ring-rose-500/40",
};

function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const refresh = async () => {
    setLoading(true);
    setErr("");
    try {
      const [j, s, r] = await Promise.all([
        listJobs(),
        getStats(),
        getLatestResume(),
      ]);
      setJobs(j);
      setStats(s);
      setResume(r);
    } catch (e) {
      setErr(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onDelete = async (id) => {
    if (!confirm("Delete this application?")) return;
    await deleteJob(id);
    refresh();
  };

  const onStatusChange = async (id, status) => {
    // Optimistic update so the pill color changes instantly
    setJobs((js) => js.map((j) => (j.id === id ? { ...j, status } : j)));
    try {
      await updateJob(id, { status });
      // Refresh stats so interview/response rates update too
      getStats().then(setStats);
    } catch (e) {
      setErr(e.message || "Failed to update status");
      refresh();
    }
  };

  if (loading) return <div className="text-slate-400">Loading…</div>;
  if (err) return <div className="text-rose-400">Error: {err}</div>;

  const pct = (v) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="text-sm text-slate-400">Overview of your job applications.</p>
      </div>

      {!resume && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-md border border-amber-700 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
          <span>
            No resume uploaded yet — upload one to enable JD analysis and match scoring.
          </span>
          <Link
            to="/resume"
            className="self-start sm:self-auto rounded-md bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-100 ring-1 ring-amber-500/40 hover:bg-amber-500/30"
          >
            Upload resume
          </Link>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total" value={stats.total_applications} />
        <StatCard label="Interview rate" value={pct(stats.interview_rate)} />
        <StatCard label="Response rate" value={pct(stats.response_rate)} />
        <StatCard
          label="Avg match"
          value={stats.avg_match_score != null ? `${stats.avg_match_score}%` : "—"}
          sub={stats.avg_match_score == null ? "Run JD Analyzer to populate" : null}
        />
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-slate-300">
          Applications ({jobs.length})
        </div>
        {jobs.length === 0 ? (
          <div className="px-4 py-6 text-sm text-slate-400">
            No applications yet. Add one from the Add Job page.
          </div>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Company</th>
                <th className="px-4 py-2 font-medium">Role</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Applied</th>
                <th className="px-4 py-2 font-medium">Match</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-t border-slate-800">
                  <td className="px-4 py-2 font-medium text-white">{j.company}</td>
                  <td className="px-4 py-2 text-slate-300">{j.role}</td>
                  <td className="px-4 py-2">
                    <select
                      value={j.status}
                      onChange={(e) => onStatusChange(j.id, e.target.value)}
                      className={`cursor-pointer rounded-full border-0 px-2 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                        STATUS_STYLES[j.status] || STATUS_STYLES.applied
                      }`}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s} className="bg-slate-900 text-slate-100">
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {new Date(j.applied_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-slate-400">
                    {j.match_score != null ? `${j.match_score}%` : "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link
                      to={`/analyze?job=${j.id}`}
                      className="mr-3 text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      analyze
                    </Link>
                    <button
                      onClick={() => onDelete(j.id)}
                      className="text-xs text-rose-400 hover:text-rose-300"
                    >
                      delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  );
}
