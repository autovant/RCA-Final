"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
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

type TicketSettings = {
  servicenow_enabled: boolean;
  jira_enabled: boolean;
  dual_mode: boolean;
};

type TicketRecord = {
  id: string;
  job_id: string;
  platform: "servicenow" | "jira";
  ticket_id: string;
  url?: string | null;
  status: string;
  profile_name?: string | null;
  dry_run: boolean;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
};

type TicketListResponse = {
  job_id: string;
  tickets: TicketRecord[];
};

const PLACEHOLDER_TICKETS: TicketRecord[] = [
  {
    id: "placeholder-servicenow",
    job_id: "demo",
    platform: "servicenow",
    ticket_id: "INC0012345",
    url: "https://example.service-now.com/nav_to.do?uri=incident.do?sys_id=demo",
    status: "In Progress",
    profile_name: null,
    dry_run: true,
    payload: {
      short_description: "Demo incident prepared from RCA summary",
      priority: "2",
    },
    metadata: {
      placeholder: true,
      synopsis: "Use this demo incident to showcase ITSM workflows when integrations are offline.",
    },
    created_at: new Date().toISOString(),
    updated_at: null,
  },
  {
    id: "placeholder-jira",
    job_id: "demo",
    platform: "jira",
    ticket_id: "OPS-1099",
    url: "https://example.atlassian.net/browse/OPS-1099",
    status: "To Do",
    profile_name: null,
    dry_run: true,
    payload: {
      summary: "Demo Jira issue created from RCA automation",
      project_key: "OPS",
    },
    metadata: {
      placeholder: true,
      synopsis: "Demonstrates dual-tracking experience for Jira when APIs are unavailable.",
    },
    created_at: new Date().toISOString(),
    updated_at: null,
  },
];

const toISO = (value?: string) =>
  value ? new Date(value).toLocaleString() : "-";

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

  const [ticketSettings, setTicketSettings] = useState<TicketSettings | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [ticketSettingsBusy, setTicketSettingsBusy] = useState(false);
  const [ticketError, setTicketError] = useState<string | null>(null);
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketFilter, setTicketFilter] = useState("");
  const [ticketAutoRefresh, setTicketAutoRefresh] = useState(true);
  const [dispatchingTickets, setDispatchingTickets] = useState(false);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobEvents, setJobEvents] = useState<JobEventEntry[]>([]);

  const [jobType, setJobType] = useState("rca_analysis");
  const [manifestText, setManifestText] = useState("{\n  \"notes\": []\n}");
  const [jobSubmitting, setJobSubmitting] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const ticketRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const api = useMemo(() => axios.create({ baseURL: API_BASE }), []);

  useEffect(() => {
    if (accessToken) {
      api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
      fetchJobs();
      fetchTicketSettings();
    } else {
      delete api.defaults.headers.common.Authorization;
      setJobs([]);
      setSelectedJobId(null);
      setJobEvents([]);
      setTicketSettings(null);
      setTickets([]);
    }
  }, [api, accessToken, fetchTicketSettings]);

  useEffect(() => {
    if (!accessToken || !selectedJobId) {
      if (!selectedJobId) {
        setTickets([]);
      }
      return;
    }

    fetchTickets(selectedJobId, true);
  }, [accessToken, selectedJobId, fetchTickets]);

  useEffect(() => {
    if (!selectedJobId || !ticketAutoRefresh) {
      if (ticketRefreshRef.current) {
        clearInterval(ticketRefreshRef.current);
        ticketRefreshRef.current = null;
      }
      return;
    }

    ticketRefreshRef.current = setInterval(() => {
      fetchTickets(selectedJobId, true);
    }, 30000);

    return () => {
      if (ticketRefreshRef.current) {
        clearInterval(ticketRefreshRef.current);
        ticketRefreshRef.current = null;
      }
    };
  }, [selectedJobId, ticketAutoRefresh, fetchTickets]);

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

  const fetchTicketSettings = useCallback(async () => {
    if (!accessToken) {
      setTicketSettings(null);
      return;
    }

    try {
      setSettingsLoading(true);
      const response = await api.get<TicketSettings>("/api/tickets/settings/state");
      setTicketSettings(response.data);
    } catch (error: any) {
      setTicketError(error?.response?.data?.detail ?? "Unable to load ticket settings");
    } finally {
      setSettingsLoading(false);
    }
  }, [accessToken, api]);

  const updateTicketSettings = async (patch: Partial<TicketSettings>) => {
    if (!accessToken) {
      return;
    }
    setTicketError(null);
    setTicketSettingsBusy(true);

    try {
      const response = await api.put<TicketSettings>("/api/tickets/settings/state", patch);
      setTicketSettings(response.data);
    } catch (error: any) {
      setTicketError(error?.response?.data?.detail ?? "Unable to update ticket settings");
    } finally {
      setTicketSettingsBusy(false);
    }
  };

  const fetchTickets = useCallback(
    async (jobId: string, refresh = false) => {
      if (!jobId) {
        return;
      }

      try {
        setTicketsLoading(true);
        setTicketError(null);
        const response = await api.get<TicketListResponse>(`/api/tickets/${jobId}`, {
          params: { refresh },
        });
        setTickets(response.data.tickets);
      } catch (error: any) {
        setTicketError(error?.response?.data?.detail ?? "Unable to load tickets");
      } finally {
        setTicketsLoading(false);
      }
    },
    [api]
  );

  const handleDispatchTickets = async (dryRun: boolean) => {
    if (!selectedJobId) {
      setTicketError("Select a job before generating tickets.");
      return;
    }

    if (
      !dryRun &&
      (!ticketSettings ||
        (!ticketSettings.servicenow_enabled && !ticketSettings.jira_enabled))
    ) {
      setTicketError("Enable at least one integration before creating live tickets.");
      return;
    }

    setDispatchingTickets(true);
    setTicketError(null);

    try {
      const response = await api.post<TicketListResponse>("/api/tickets/dispatch", {
        job_id: selectedJobId,
        payloads: {},
        dry_run: dryRun,
      });
      setTickets(response.data.tickets);
    } catch (error: any) {
      setTicketError(error?.response?.data?.detail ?? "Ticket dispatch failed");
    } finally {
      setDispatchingTickets(false);
    }
  };

  const filteredTickets = useMemo(() => {
    if (!ticketFilter.trim()) {
      return tickets;
    }
    const needle = ticketFilter.toLowerCase();
    return tickets.filter((ticket) => {
      const segments = [
        ticket.ticket_id,
        ticket.status,
        ticket.platform,
        JSON.stringify(ticket.payload ?? {}),
        JSON.stringify(ticket.metadata ?? {}),
      ];
      return segments.some((segment) =>
        segment ? segment.toLowerCase().includes(needle) : false
      );
    });
  }, [tickets, ticketFilter]);

  const groupedTickets = useMemo(() => {
    const base: Record<"servicenow" | "jira", TicketRecord[]> = {
      servicenow: [],
      jira: [],
    };
    filteredTickets.forEach((ticket) => {
      base[ticket.platform].push(ticket);
    });
    return base;
  }, [filteredTickets]);

  const placeholderGroups = useMemo(() => {
    const base: Record<"servicenow" | "jira", TicketRecord[]> = {
      servicenow: [],
      jira: [],
    };
    PLACEHOLDER_TICKETS.forEach((ticket) => {
      base[ticket.platform].push(ticket);
    });
    return base;
  }, []);

  const dualModeActive =
    !!ticketSettings?.dual_mode &&
    !!ticketSettings?.servicenow_enabled &&
    !!ticketSettings?.jira_enabled;

  const togglesDisabled = settingsLoading || ticketSettingsBusy;

  const platformMeta = {
    servicenow: {
      title: "ServiceNow Incidents",
      accent: "border-emerald-500/60",
      badge: "border border-emerald-500/40 text-emerald-300",
      description: "INC lifecycle synced from RCA insights.",
      enabled: !!ticketSettings?.servicenow_enabled,
    },
    jira: {
      title: "Jira Issues",
      accent: "border-sky-500/60",
      badge: "border border-sky-500/40 text-sky-300",
      description: "Engineering work tracked via Jira automation.",
      enabled: !!ticketSettings?.jira_enabled,
    },
  } as const;

  const statusTone = (status: string) => {
    const normalised = status.toLowerCase();
    if (normalised.includes("progress") || normalised.includes("working")) {
      return "border border-amber-500/40 bg-amber-500/10 text-amber-200";
    }
    if (
      normalised.includes("resolve") ||
      normalised.includes("closed") ||
      normalised.includes("done")
    ) {
      return "border border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
    }
    if (normalised.includes("fail") || normalised.includes("error")) {
      return "border border-rose-500/40 bg-rose-500/10 text-rose-200";
    }
    if (normalised.includes("dry")) {
      return "border border-slate-600 bg-slate-800/60 text-slate-200";
    }
    return "border border-sky-500/40 bg-sky-500/10 text-sky-200";
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

      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl shadow-black/30 space-y-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold text-white">Ticket automation cockpit</h2>
            <p className="text-sm text-slate-400">
              Control ServiceNow and Jira ticket creation, then monitor statuses without leaving the RCA console.
            </p>
            {selectedJobId ? (
              <p className="text-xs font-mono text-slate-500">Selected job: {selectedJobId}</p>
            ) : (
              <p className="text-xs text-slate-500">Select a job to enable ticket orchestration actions.</p>
            )}
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <button
              type="button"
              onClick={() => handleDispatchTickets(true)}
              disabled={!selectedJobId || dispatchingTickets}
              className="rounded border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-400 disabled:cursor-not-allowed disabled:border-slate-800 disabled:text-slate-600"
            >
              {dispatchingTickets ? "Dispatching..." : "Preview Tickets"}
            </button>
            <button
              type="button"
              onClick={() => handleDispatchTickets(false)}
              disabled={
                !selectedJobId ||
                dispatchingTickets ||
                !ticketSettings ||
                (!ticketSettings.servicenow_enabled && !ticketSettings.jira_enabled)
              }
              className="rounded bg-indigo-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-indigo-900"
            >
              {dispatchingTickets ? "Submitting..." : "Create Live Tickets"}
            </button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <label className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <span>ServiceNow</span>
            <input
              type="checkbox"
              className="h-4 w-4 accent-emerald-500"
              disabled={togglesDisabled || !ticketSettings}
              checked={!!ticketSettings?.servicenow_enabled}
              onChange={() =>
                ticketSettings &&
                updateTicketSettings({ servicenow_enabled: !ticketSettings.servicenow_enabled })
              }
            />
          </label>
          <label className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <span>Jira</span>
            <input
              type="checkbox"
              className="h-4 w-4 accent-sky-500"
              disabled={togglesDisabled || !ticketSettings}
              checked={!!ticketSettings?.jira_enabled}
              onChange={() =>
                ticketSettings &&
                updateTicketSettings({ jira_enabled: !ticketSettings.jira_enabled })
              }
            />
          </label>
          <label className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <span>Dual tracking</span>
            <input
              type="checkbox"
              className="h-4 w-4 accent-purple-500"
              disabled={
                togglesDisabled ||
                !ticketSettings ||
                !(ticketSettings.servicenow_enabled && ticketSettings.jira_enabled)
              }
              checked={!!ticketSettings?.dual_mode}
              onChange={() =>
                ticketSettings &&
                updateTicketSettings({ dual_mode: !ticketSettings.dual_mode })
              }
            />
          </label>
          <label className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200">
            <span>Auto refresh</span>
            <input
              type="checkbox"
              className="h-4 w-4 accent-amber-500"
              checked={ticketAutoRefresh}
              onChange={() => setTicketAutoRefresh((value) => !value)}
            />
          </label>
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <label className="flex w-full max-w-md flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-slate-400">Search tickets</span>
            <input
              className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="Filter by ticket id, status, platform, payload..."
              value={ticketFilter}
              onChange={(event) => setTicketFilter(event.target.value)}
            />
          </label>
          {dualModeActive ? (
            <span className="inline-flex items-center gap-2 self-start rounded-full border border-purple-500/40 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-200">
              Dual mode active
            </span>
          ) : null}
        </div>

        {ticketError ? <p className="text-sm text-rose-400">{ticketError}</p> : null}

        <div className="grid gap-5 md:grid-cols-2">
          {(Object.keys(platformMeta) as Array<"servicenow" | "jira">).map((platform) => {
            const meta = platformMeta[platform];
            const activeTickets = groupedTickets[platform];
            const showPlaceholder = activeTickets.length === 0;
            const ticketsToRender = showPlaceholder ? placeholderGroups[platform] : activeTickets;

            return (
              <div
                key={platform}
                className={`rounded-xl border ${meta.accent} bg-slate-950/60 p-4 space-y-3`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold capitalize text-white">{meta.title}</h3>
                    <p className="text-xs text-slate-400">{meta.description}</p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs uppercase tracking-wide ${
                      meta.enabled ? meta.badge : "border border-slate-700 text-slate-500"
                    }`}
                  >
                    {meta.enabled ? "enabled" : "disabled"}
                  </span>
                </div>

                {ticketsLoading && !activeTickets.length ? (
                  <p className="text-sm text-slate-500">Refreshing ticket status…</p>
                ) : null}

                <div className="space-y-3">
                  {ticketsToRender.map((ticket) => (
                    <article
                      key={ticket.id}
                      className="rounded-lg border border-slate-800 bg-slate-900/80 p-3 text-sm text-slate-200"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className={`rounded-full px-2 py-0.5 ${statusTone(ticket.status || "")}`}>
                          {ticket.status || (ticket.dry_run ? "dry-run" : "new")}
                        </span>
                        <span className="font-mono text-slate-500">{ticket.ticket_id}</span>
                      </div>
                      <div className="mt-2 space-y-1">
                        <p className="text-xs text-slate-400">
                          {ticket.payload?.short_description || ticket.payload?.summary || "Generated ticket payload"}
                        </p>
                        {ticket.url ? (
                          <a
                            href={ticket.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-indigo-400 hover:text-indigo-300"
                          >
                            Open in {platform === "jira" ? "Jira" : "ServiceNow"}
                          </a>
                        ) : null}
                        {ticket.dry_run ? (
                          <p className="text-xs text-amber-400">
                            Dry-run preview only. Submit live tickets to push to {platform}.
                          </p>
                        ) : null}
                        {ticket.metadata?.placeholder &&
                        typeof (ticket.metadata?.synopsis as string | undefined) === "string" ? (
                          <p className="text-xs text-slate-500">
                            {(ticket.metadata.synopsis as string) ?? ""}
                          </p>
                        ) : null}
                      </div>
                      <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500">
                        <span>Created: {toISO(ticket.created_at ?? undefined)}</span>
                        {ticket.metadata?.linked_servicenow ? (
                          <span>
                            Linked INC:{" "}
                            {(ticket.metadata.linked_servicenow as Record<string, string>)?.ticket_id ?? "unknown"}
                          </span>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            );
          })}
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
