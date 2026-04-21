import axios from "axios";

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api",
});

export const listJobs = (params) => api.get("/jobs", { params }).then((r) => r.data);
export const createJob = (job) => api.post("/jobs", job).then((r) => r.data);
export const updateJob = (id, job) => api.put(`/jobs/${id}`, job).then((r) => r.data);
export const deleteJob = (id) => api.delete(`/jobs/${id}`).then((r) => r.data);
export const getStats = () => api.get("/stats").then((r) => r.data);
export const sendChat = (message) =>
  api.post("/chat", { message }).then((r) => r.data);

export const uploadResume = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post("/resume", form, { headers: { "Content-Type": "multipart/form-data" } })
    .then((r) => r.data);
};

export const getLatestResume = () =>
  api
    .get("/resume/latest")
    .then((r) => r.data)
    .catch((e) => {
      if (e.response?.status === 404) return null;
      throw e;
    });

export const analyzeJD = ({ jd_text, job_id }) =>
  api.post("/analyze", { jd_text, job_id }).then((r) => r.data);
