import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob } from "../api";

const EMPTY = {
  company: "",
  role: "",
  status: "applied",
  url: "",
  location: "",
  salary: "",
  notes: "",
  jd_text: "",
};

export default function AddJob() {
  const nav = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErr("");
    try {
      // Strip empty optional fields
      const payload = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v !== "")
      );
      const created = await createJob(payload);
      if (form.jd_text.trim()) {
        nav(`/analyze?job=${created.id}`);
      } else {
        nav("/");
      }
    } catch (e2) {
      setErr(e2.response?.data?.detail || e2.message || "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  const inputCls =
    "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Add Job Application</h1>
        <p className="text-sm text-slate-400">
          Paste the JD text if you want to run a resume-match analysis later.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Company *</label>
            <input
              required
              className={inputCls}
              value={form.company}
              onChange={update("company")}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Role *</label>
            <input
              required
              className={inputCls}
              value={form.role}
              onChange={update("role")}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Status</label>
            <select
              className={inputCls}
              value={form.status}
              onChange={update("status")}
            >
              <option value="applied">Applied</option>
              <option value="interview">Interview</option>
              <option value="offer">Offer</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Location</label>
            <input
              className={inputCls}
              value={form.location}
              onChange={update("location")}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">URL</label>
            <input
              className={inputCls}
              value={form.url}
              onChange={update("url")}
              placeholder="https://…"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Salary</label>
            <input
              className={inputCls}
              value={form.salary}
              onChange={update("salary")}
              placeholder="e.g. $130k"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-300">Notes</label>
          <textarea
            rows={3}
            className={inputCls}
            value={form.notes}
            onChange={update("notes")}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-300">JD text (optional)</label>
          <textarea
            rows={6}
            className={inputCls}
            value={form.jd_text}
            onChange={update("jd_text")}
            placeholder="Paste the full job description here…"
          />
        </div>

        {err && <div className="text-sm text-rose-400">{err}</div>}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={() => nav("/")}
            className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
