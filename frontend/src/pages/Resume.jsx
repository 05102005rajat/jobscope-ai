import { useEffect, useRef, useState } from "react";
import { getLatestResume, uploadResume } from "../api";

export default function Resume() {
  const [current, setCurrent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const refresh = async () => {
    setLoading(true);
    try {
      setCurrent(await getLatestResume());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErr("Only PDF files are supported.");
      return;
    }
    setErr("");
    setUploading(true);
    try {
      await uploadResume(file);
      await refresh();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Resume</h1>
        <p className="text-sm text-slate-400">
          Upload a PDF. We extract your technical skills with an LLM so the JD
          analyzer can find what's missing from each job description.
        </p>
      </div>

      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragActive
            ? "border-indigo-400 bg-indigo-500/10"
            : "border-slate-700 bg-slate-900 hover:border-slate-500"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {uploading ? (
          <div className="text-sm text-slate-300">Uploading & extracting skills…</div>
        ) : (
          <>
            <div className="text-sm text-slate-300">
              Drop a PDF here, or click to choose a file
            </div>
            <div className="mt-1 text-xs text-slate-500">PDF only</div>
          </>
        )}
      </div>

      {err && <div className="text-sm text-rose-400">{err}</div>}

      <div className="rounded-lg border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-slate-300">
          Current resume
        </div>
        <div className="p-4">
          {loading ? (
            <div className="text-sm text-slate-400">Loading…</div>
          ) : !current ? (
            <div className="text-sm text-slate-400">
              No resume uploaded yet.
            </div>
          ) : (
            <>
              <div className="flex items-baseline justify-between">
                <div className="font-medium text-white">{current.filename}</div>
                <div className="text-xs text-slate-500">
                  Uploaded {new Date(current.uploaded_date).toLocaleString()}
                </div>
              </div>
              <div className="mt-4">
                <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">
                  Extracted skills ({current.skills?.length || 0})
                </div>
                <div className="flex flex-wrap gap-2">
                  {(current.skills || []).map((s) => (
                    <span
                      key={s}
                      className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-200 ring-1 ring-slate-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
