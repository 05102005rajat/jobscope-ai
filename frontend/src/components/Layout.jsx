import { NavLink, Outlet } from "react-router-dom";

const linkCls = ({ isActive }) =>
  `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? "bg-indigo-600 text-white"
      : "text-slate-300 hover:bg-slate-800 hover:text-white"
  }`;

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto max-w-5xl flex items-center gap-4 px-6 py-3">
          <div className="text-lg font-semibold tracking-tight">
            JobScope <span className="text-indigo-400">AI</span>
          </div>
          <div className="ml-6 flex gap-2">
            <NavLink to="/" end className={linkCls}>Dashboard</NavLink>
            <NavLink to="/add" className={linkCls}>Add Job</NavLink>
            <NavLink to="/resume" className={linkCls}>Resume</NavLink>
            <NavLink to="/analyze" className={linkCls}>Analyze</NavLink>
            <NavLink to="/chat" className={linkCls}>Chat</NavLink>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
