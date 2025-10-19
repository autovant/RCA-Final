# UI Progress Events Integration - Complete

## Changes Made to StreamingChat.tsx

### 1. Updated Step Definitions
Added new steps to match the backend progress events:

```typescript
const STEP_DEFINITIONS: StepDefinition[] = [
  { id: "classification", label: "Classifying uploaded files", ... },
  { id: "redaction", label: "Scanning and redacting sensitive data", ... },
  { id: "chunking", label: "Segmenting content into analysis-ready chunks", ... },
  { id: "embedding", label: "Generating semantic embeddings", ... },
  { id: "storage", label: "Storing structured insights", ... },
  { id: "correlation", label: "Correlating with historical incidents", ... },  // NEW
  { id: "llm", label: "Running AI-powered root cause analysis", ... },
  { id: "report", label: "Preparing final RCA report", ... },
  { id: "completed", label: "Analysis completed successfully", ... },  // NEW
];
```

### 2. Added Progress Percentage Tracking
- Added `progressPercentage` state to track overall progress (0-100%)
- Updates from `details.progress` in `analysis-progress` events
- Resets to 0 when new job starts

### 3. Enhanced Event Handling

#### New "ready" Event Handler
```typescript
case "ready": {
  const readyMessage = typeof data.message === "string" 
    ? data.message 
    : "Job ready for processing.";
  pushLog(readyMessage, "info", timestamp);
  break;
}
```

#### Updated "started" Event Handler
```typescript
case "running":
case "started": {
  handleStatusUpdate("running");
  updateStep("classification", "in-progress", { timestamp });
  pushLog("Analysis started.", "info", timestamp);
  break;
}
```

#### Enhanced "analysis-progress" Handler
```typescript
case "analysis-progress": {
  // Extract progress percentage from details
  if (details && typeof details.progress === "number") {
    setProgressPercentage(details.progress);
  }
  
  // Special handling for completion event
  if (stepId === "completed" && stepStatus === "completed") {
    handleStatusUpdate("completed");
    setProgressPercentage(100);
  }
  
  // ... rest of handler
}
```

### 4. Added Visual Progress Bar
Located in the header section, displays when `progressPercentage > 0`:

```tsx
{jobId && progressPercentage > 0 && (
  <div className="mt-4">
    <div className="mb-1 flex items-center justify-between text-xs">
      <span className="text-dark-text-secondary">Overall Progress</span>
      <span className="font-semibold text-fluent-blue-400">{progressPercentage}%</span>
    </div>
    <div className="h-2 w-full overflow-hidden rounded-full bg-dark-bg-tertiary">
      <div
        className="h-full rounded-full bg-gradient-to-r from-fluent-blue-500 to-fluent-info transition-all duration-500 ease-out"
        style={{ width: `${progressPercentage}%` }}
      />
    </div>
  </div>
)}
```

## Event Flow Mapping

### Backend Events → UI Display

| Backend Event | Step ID | UI Label | Progress % |
|--------------|---------|----------|-----------|
| `classification` started | classification | "Classifying uploaded files" | 0% |
| `classification` completed | classification | "Classifying uploaded files" | 10% |
| `redaction` started | redaction | "Scanning and redacting..." | 10-40% |
| `redaction` completed | redaction | "Scanning and redacting..." | 40% |
| `chunking` started | chunking | "Segmenting content..." | 40-50% |
| `chunking` completed | chunking | "Segmenting content..." | 50% |
| `embedding` started | embedding | "Generating embeddings" | 50-60% |
| `embedding` completed | embedding | "Generating embeddings" | 60% |
| `storage` started | storage | "Storing insights" | 60-70% |
| `storage` completed | storage | "Storing insights" | 70% |
| `correlation` started | correlation | "Correlating with historical..." | 70% |
| `correlation` completed | correlation | "Correlating with historical..." | 75% |
| `llm` started | llm | "Running AI-powered RCA" | 75% |
| `llm` completed | llm | "Running AI-powered RCA" | 90% |
| `report` started | report | "Preparing final RCA report" | 90% |
| `report` completed | report | "Preparing final RCA report" | 100% |
| `completed` success | completed | "Analysis completed successfully" | 100% |

## Testing Instructions

### 1. Start the Development Environment

```powershell
# In Terminal 1 - Backend & Worker (already running)
.\quick-start-dev.ps1

# In Terminal 2 - Frontend UI
cd ui
npm run dev
```

### 2. Access the Investigation Page

Navigate to: **http://localhost:3000/investigation**

### 3. Upload a Test File

1. Click the **"Upload Files"** button
2. Select `test-error.log` (or any .log file)
3. Click **"Start Analysis"**

### 4. Observe Real-Time Progress

You should see:

#### Header Section:
- **Status Badge**: Changes from "Ready" → "Queued" → "Running" → "Completed"
- **Live Indicator**: Green pulsing dot when connected
- **Progress Bar**: Smoothly animates from 0% → 100%
- **Last Update Time**: Updates with each event

#### Analysis Progress Section:
9 steps displayed with status icons:
- ⚪ Pending (gray circle)
- 🔵 In-Progress (pulsing blue circle)
- ✅ Completed (green checkmark)
- ❌ Failed (red exclamation)

Each step shows:
- Step label (e.g., "Classifying uploaded files")
- Current message (e.g., "Classified 1 file - proceeding with RCA analysis.")
- Last update timestamp

#### Activity Log Section:
Scrolling list of timestamped events with colored indicators:
- 🟦 Blue - Info messages
- 🟩 Green - Success messages
- 🟨 Yellow - Warning messages
- 🟥 Red - Error messages

### 5. Expected Event Timeline

For a single file upload (test-error.log):

```
[16:08:32] Files queued for analysis.
[16:08:34] Connected to analysis stream.
[16:08:34] Analysis started.
[16:08:34] Classifying uploaded files and preparing analysis pipeline...
[16:08:34] Classified 1 file - proceeding with RCA analysis.
[16:08:34] Processing test-error.log...
[16:08:34] Scanning test-error.log (1/1) for sensitive data...
[16:08:35] Segmenting test-error.log (1/1) into analysis chunks...
[16:08:35] Segmented 1 chunk from test-error.log (1/1).
[16:08:35] Generating embeddings for test-error.log (1/1)...
[16:08:35] Generated embeddings for 1 segment from test-error.log (1/1).
[16:08:35] Storing analysis artefacts for test-error.log (1/1)...
[16:08:35] Stored 1 document for test-error.log (1/1).
[16:08:35] Masked 5 sensitive items in test-error.log.
[16:08:35] Searching for similar historical incidents and patterns...
[16:08:36] Correlation complete - analyzed patterns across 1 data chunks.
[16:08:36] Running AI-powered root cause analysis using GitHub Copilot...
[16:08:36] Running analysis with copilot/gpt-4...
[16:08:38] Root cause analysis draft generated.
[16:08:38] AI analysis complete - identified root causes and recommendations.
[16:08:38] Compiling comprehensive RCA report with findings and recommendations...
[16:08:42] RCA report generated successfully! Analyzed 5 lines across 1 file(s).
[16:08:42] ✓ Analysis complete! Root cause identified and report ready for review.
[16:08:42] Analysis completed successfully.
```

### 6. Verify SSE Connection

Open browser DevTools (F12) → Network tab:
- Look for request to `/api/jobs/{jobId}/stream`
- Type should be `eventsource`
- Status should be `200` with streaming indicator
- Messages tab shows real-time events

### 7. Check for Issues

Common issues and solutions:

#### No Connection / "Offline" Indicator
- **Check**: Backend is running on port 8001
- **Fix**: Restart backend with `.\quick-start-dev.ps1`
- **Verify**: Visit http://localhost:8001/api/docs

#### Events Not Appearing
- **Check**: Browser console for errors
- **Check**: Network tab for SSE connection
- **Fix**: Clear browser cache and refresh
- **Verify**: Events are being generated (check backend logs)

#### Progress Bar Not Moving
- **Check**: `details.progress` field in events
- **Check**: Browser console for JavaScript errors
- **Verify**: Backend is sending progress percentages

#### Wrong Step Labels
- **Check**: `STEP_DEFINITIONS` in StreamingChat.tsx matches backend `PROGRESS_STEP_LABELS`
- **Fix**: Update step IDs if backend changed

## Architecture

### SSE Connection Flow

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Frontend UI   │         │   FastAPI SSE    │         │  Job Processor  │
│ StreamingChat   │◄────────│  /jobs/{id}/     │◄────────│   (Worker)      │
│                 │  SSE    │     stream       │  Events │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │                            │
        │ 1. Connect EventSource     │                            │
        │──────────────────────────►│                            │
        │                            │                            │
        │ 2. SSE: job-event         │                            │
        │◄──────────────────────────│                            │
        │    {type: "analysis-      │  3. emit_progress_event()  │
        │     progress", ...}        │◄───────────────────────────│
        │                            │                            │
        │ 4. Update UI              │                            │
        │   - Progress bar          │                            │
        │   - Step status           │                            │
        │   - Activity log          │                            │
        │                            │                            │
```

### Event Processing Pipeline

```typescript
EventSource.addEventListener("job-event", (event) => {
  const payload = JSON.parse(event.data);  // Parse SSE data
  processJobEvent(payload);                 // Route to handler
  
  switch (payload.event_type) {
    case "analysis-progress":
      setProgressPercentage(data.details.progress);  // Update progress bar
      updateStep(data.step, status, { ... });         // Update step UI
      pushLog(data.message, variant, timestamp);      // Add to activity log
      break;
    // ... other event types
  }
});
```

## Performance Metrics

Expected performance for typical file upload:

| Metric | Target | Notes |
|--------|--------|-------|
| SSE Connection Time | < 100ms | EventSource initialization |
| First Event Display | < 200ms | "Connected to stream" message |
| Event Processing | < 10ms | Per event handler execution |
| UI Update Latency | < 50ms | React state update + render |
| Total Events | 20-35 | Depends on file count |
| Progress Bar Animation | 500ms | CSS transition duration |
| Log Auto-Scroll | Smooth | IntersectionObserver-based |

## Next Steps

1. ✅ Backend progress events implemented
2. ✅ UI event handling updated
3. ✅ Progress bar added
4. ✅ Step definitions synchronized
5. 🔄 **Test end-to-end** (upload file via UI)
6. 🔄 Verify all 9 steps display correctly
7. 🔄 Confirm progress bar animates smoothly
8. 🔄 Check activity log shows all messages
9. ⏭️ Add error state handling (network failures)
10. ⏭️ Add retry logic for disconnections

## Status

**✅ IMPLEMENTATION COMPLETE**

The UI is now fully configured to:
- Connect to SSE endpoint at `/api/jobs/{jobId}/stream`
- Display 9 analysis steps with real-time status updates
- Show overall progress percentage (0-100%)
- Log all events with timestamps and colored indicators
- Handle connection status (online/offline)
- Auto-scroll to latest log entries
- Update step descriptions with custom messages

**Ready for end-to-end testing!** 🚀
