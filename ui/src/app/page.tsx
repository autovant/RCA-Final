"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import axios from "axios";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type JobResponse = {
  id: string;
  job_type: string;
  status: string;
  user_id: string;
  created_at?: string;
  updated_at?: string;
};

type JobEventPayload = Record<string, unknown>;

type JobEventEntry = {
  event: string;
  payload: JobEventPayload;
  receivedAt: string;
};

const toISO = (value?: string) =>
  value ? new Date(value).toLocaleString() : "—";

export default function HomePage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState("anonymous");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobEvents, setJobEvents] = useState<JobEventEntry[]>([]);

  const [jobType, setJobType] = useState("rca_analysis");
  const [manifestText, setManifestText] = useState("{\n  \"notes\": []\n}");
  const [jobSubmitting, setJobSubmitting] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const api = useMemo(() => axios.create({ baseURL: API_BASE }), []);

  useEffect(() => {
    if (accessToken) {
      api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
      fetchJobs();
    } else {
      delete api.defaults.headers.common.Authorization;
      setJobs([]);
      setSelectedJobId(null);
      setJobEvents([]);
    }
  }, [api, accessToken]);

  const fetchJobs = async () => {
    try {
      setJobsLoading(true);
      const response = await api.get<JobResponse[]>("/api/jobs");
      setJobs(response.data);
    } catch (error: any) {
      setJobError(error?.response?.data?.detail ?? "Unable to load jobs");
    } finally {
      setJobsLoading(false);
    }
  };

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setLoginError(null);

    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await axios.post(
        `${API_BASE}/api/auth/login`,
        formData,
        {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        }
      );

      setAccessToken(response.data.access_token);
      setRefreshToken(response.data.refresh_token);
    } catch (error: any) {
      setLoginError(error?.response?.data?.detail ?? "Login failed");
      setAccessToken(null);
      setRefreshToken(null);
    }
  };

  const handleRefreshToken = async () => {
    if (!refreshToken) {
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/api/auth/refresh`, {
        refresh_token: refreshToken,
      });
      setAccessToken(response.data.access_token);
      setRefreshToken(response.data.refresh_token);
    } catch (error: any) {
      setLoginError(error?.response?.data?.detail ?? "Refresh failed");
    }
  };

  const handleCreateJob = async (event: FormEvent) => {
    event.preventDefault();
    setJobError(null);

    let parsedManifest: Record<string, unknown>;
    try {
      parsedManifest = JSON.parse(manifestText || "{}");
    } catch (err) {
      setJobError("Input manifest must be valid JSON.");
      return;
    }

    try {
      setJobSubmitting(true);
      const response = await api.post<JobResponse>("/api/jobs", {
        user_id: userId || "anonymous",
        job_type: jobType,
        input_manifest: parsedManifest,
      });
      setJobs((prev) => [response.data, ...prev]);
      setSelectedJobId(response.data.id);
      setJobEvents([]);
    } catch (error: any) {
      setJobError(error?.response?.data?.detail ?? "Failed to create job");
    } finally {
      setJobSubmitting(false);
    }
  };

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedJobId) {
      setUploadMessage("Select a job before uploading files.");
      return;
    }

    const formData = new FormData(event.currentTarget);
    formData.append("job_id", selectedJobId);

    try {
      setUploading(true);
      const response = await api.post("/api/files/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadMessage(`Uploaded ${response.data.original_filename}`);
      event.currentTarget.reset();
    } catch (error: any) {
      setUploadMessage(
        error?.response?.data?.detail ?? "Upload failed. Check file policy."
      );
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    if (!selectedJobId) {
      setJobEvents([]);
      return;
    }

    const source = new EventSource(
      `${API_BASE}/api/sse/jobs/${selectedJobId}`
    );

    const handleMessage = (event: MessageEvent) => {
      const payload = JSON.parse(event.data || "{}");
      setJobEvents((prev) => [
        {
          event: event.type,
          payload,
          receivedAt: new Date().toLocaleTimeString(),
        },
        ...prev,
      ]);
      if (event.type === "complete") {
        fetchJobs();
      }
    };

    source.onmessage = handleMessage;
    source.addEventListener("heartbeat", handleMessage);
    source.addEventListener("complete", handleMessage);

    return () => {
      source.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedJobId]);

  return (
    <main className="space-y-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-white">
          RCA Engine Console
        </h1>
        <p className="text-sm text-slate-300">
          Authenticate, launch jobs, upload datasets, and observe live progress
          streamed from the worker fleet.
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/30 space-y-4">
        <h2 className="text-xl font-semibold text-white">Authentication</h2>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={handleLogin}>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              Username
            </span>
            <input
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              placeholder="engineer@example.com"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              Password
            </span>
            <input
              type="password"
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <div className="flex items-end gap-3">
            <button
              type="submit"
              className="w-full rounded bg-blue-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-blue-400"
            >
              Sign in
            </button>
            {refreshToken ? (
              <button
                type="button"
                onClick={handleRefreshToken}
                className="rounded border border-slate-600 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-400"
              >
                Refresh token
              </button>
            ) : null}
          </div>
        </form>
        {loginError ? (
          <p className="text-sm text-red-400">{loginError}</p>
        ) : null}
        {accessToken ? (
          <div className="grid gap-1 text-xs text-slate-400">
            <div>
              <span className="font-semibold text-slate-300">
                Access token:
              </span>{" "}
              <code className="break-all text-slate-500">{accessToken}</code>
            </div>
            {refreshToken ? (
              <div>
                <span className="font-semibold text-slate-300">
                  Refresh token:
                </span>{" "}
                <code className="break-all text-slate-500">{refreshToken}</code>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/30 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold text-white">Jobs</h2>
          <button
            onClick={fetchJobs}
            className="rounded border border-slate-600 px-3 py-1.5 text-xs text-slate-200 transition hover:border-slate-400"
          >
            Refresh jobs
          </button>
        </div>
        <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreateJob}>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              User ID
            </span>
            <input
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              Job type
            </span>
            <select
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              value={jobType}
              onChange={(event) => setJobType(event.target.value)}
            >
              <option value="rca_analysis">Root cause analysis</option>
              <option value="log_analysis">Log analysis</option>
              <option value="embedding_generation">Embedding generation</option>
            </select>
          </label>
          <label className="md:col-span-2 flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              Input Manifest (JSON)
            </span>
            <textarea
              className="min-h-[120px] rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono focus:border-blue-500 focus:outline-none"
              value={manifestText}
              onChange={(event) => setManifestText(event.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={jobSubmitting}
            className="md:col-span-2 rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-emerald-800"
          >
            {jobSubmitting ? "Creating job..." : "Create job"}
          </button>
        </form>
        {jobError ? <p className="text-sm text-red-400">{jobError}</p> : null}

        <div className="rounded-lg border border-slate-800 bg-slate-950/50">
          <table className="min-w-full divide-y divide-slate-800 text-sm">
            <thead className="bg-slate-900/80 text-slate-300">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Job</th>
                <th className="px-3 py-2 text-left font-medium">Status</th>
                <th className="px-3 py-2 text-left font-medium">Created</th>
                <th className="px-3 py-2 text-left font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {jobsLoading ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-6 text-center text-slate-500"
                  >
                    Loading jobs...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-6 text-center text-slate-500"
                  >
                    No jobs yet. Submit one above to get started.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr
                    key={job.id}
                    className={
                      selectedJobId === job.id
                        ? "bg-slate-900/60"
                        : "hover:bg-slate-900/40"
                    }
                  >
                    <td className="px-3 py-2 font-mono text-xs text-slate-400">
                      {job.id}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-slate-800 px-2 py-1 text-xs uppercase tracking-wide text-slate-300">
                        {job.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {toISO(job.created_at)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-200 transition hover:border-slate-400"
                        onClick={() => {
                          setSelectedJobId(job.id);
                          setJobEvents([]);
                        }}
                      >
                        Inspect events
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/30 space-y-4">
        <h2 className="text-xl font-semibold text-white">File uploads</h2>
        <p className="text-sm text-slate-400">
          Upload supporting artefacts (logs, manifests, telemetry) to attach
          them to the selected job. Files are scanned and catalogued before the
          worker begins ingesting them.
        </p>
        <form className="space-y-3" onSubmit={handleUpload}>
          <label className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">
              File
            </span>
            <input
              type="file"
              name="file"
              required
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </label>
          <button
            disabled={!selectedJobId || uploading}
            className="rounded bg-indigo-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-indigo-800"
          >
            {uploading ? "Uploading..." : "Upload to selected job"}
          </button>
        </form>
        {uploadMessage ? (
          <p className="text-sm text-slate-300">{uploadMessage}</p>
        ) : (
          <p className="text-xs text-slate-500">
            Accepted extensions: .log, .txt, .json, .yaml (configurable).
          </p>
        )}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/30 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">
            Live job events {selectedJobId ? `— ${selectedJobId}` : ""}
          </h2>
          {selectedJobId ? (
            <button
              onClick={() => setJobEvents([])}
              className="rounded border border-slate-600 px-3 py-1 text-xs text-slate-200 transition hover:border-slate-400"
            >
              Clear view
            </button>
          ) : null}
        </div>
        {selectedJobId ? (
          <div className="space-y-2">
            {jobEvents.length === 0 ? (
              <p className="text-sm text-slate-400">
                Waiting for events from the worker...
              </p>
            ) : (
              <ul className="space-y-2">
                {jobEvents.map((entry, index) => (
                  <li
                    key={`${index}-${entry.receivedAt}`}
                    className="rounded border border-slate-800 bg-slate-950/60 p-3 text-sm"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="uppercase tracking-wide text-slate-300">
                        {entry.event}
                      </span>
                      <span>{entry.receivedAt}</span>
                    </div>
                    <pre className="mt-2 overflow-x-auto rounded bg-slate-900/80 p-2 text-xs text-slate-300">
                      {JSON.stringify(entry.payload, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">
            Select a job to stream its lifecycle events.
          </p>
        )}
      </section>
    </main>
  );
}
