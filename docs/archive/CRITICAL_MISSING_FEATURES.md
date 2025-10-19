# Critical Missing Features - Investigation Interface

## 🚨 **CRITICAL ISSUES IDENTIFIED**

### 1. **"Start Guided Investigation" Button Does Nothing**

**Current Behavior:**
- Button exists in `CommandCenter.tsx`
- OnClick just scrolls to ticket creation form (`handleStartInvestigation` in `tickets/page.tsx`)
- No actual job creation or investigation workflow

**Expected Behavior:**
- Should navigate to dedicated investigation/analysis page
- Should allow file upload
- Should create a new RCA job
- Should show live streaming updates

---

### 2. **File Upload Interface is COMPLETELY MISSING**

**What's Missing:**
- No file upload component in the UI
- No drag-and-drop interface
- No file picker
- Backend has `/api/files/upload` endpoint but no UI to use it

**Backend API Available:**
```
POST /api/files/upload
- multipart/form-data
- Accepts: logs, traces, configs, docs
- Returns: file_id for job association
```

---

### 3. **Chat/Streaming Interface is COMPLETELY MISSING**

**What's Missing:**
- No chat interface showing live updates
- No SSE (Server-Sent Events) integration
- No real-time job progress display
- No conversation/turn display

**Backend SSE Endpoints Available:**
```
GET /api/jobs/{id}/stream         # Job events stream
GET /api/sse/jobs/{job_id}         # Alternative SSE endpoint
GET /api/watcher/events            # File watcher events
```

---

## 📋 **Current UI State**

### What EXISTS:
✅ Home page with stats
✅ Jobs list (read-only, preview mode)
✅ Tickets dashboard (read-only)
✅ Ticket creation form (for ITSM sync, not investigation)

### What's MISSING:
❌ Investigation/Analysis page
❌ File upload component
❌ Chat interface
❌ Real-time streaming updates
❌ Job creation workflow
❌ Live progress indicators
❌ File management (list uploaded files)

---

## 🎯 **Required Features to Implement**

### 1. **Investigation Page** (`/investigation` or `/analyze`)

**Requirements:**
- [ ] Route: `/app/investigation/page.tsx`
- [ ] File upload dropzone
- [ ] File list display
- [ ] Job configuration form
- [ ] Chat/streaming interface
- [ ] "Start Analysis" button → creates job
- [ ] Live progress updates via SSE

### 2. **File Upload Component**

**Requirements:**
- [ ] Drag-and-drop zone
- [ ] File picker button
- [ ] File type validation (logs, configs, traces, docs)
- [ ] Upload progress bar
- [ ] File list with remove option
- [ ] Integration with `/api/files/upload`

### 3. **Chat/Streaming Component**

**Requirements:**
- [ ] SSE connection to `/api/jobs/{id}/stream`
- [ ] Message display (user + assistant turns)
- [ ] Live updates as job progresses
- [ ] Status indicators (queued, running, completed, failed)
- [ ] Error handling and reconnection
- [ ] Conversation history

### 4. **Job Creation Workflow**

**Requirements:**
- [ ] Form to configure job parameters:
  - Job type (rca_analysis)
  - Provider (ollama, openai, etc.)
  - Model selection
  - Priority
- [ ] File association (link uploaded files to job)
- [ ] POST to `/api/jobs` to create job
- [ ] Navigate to streaming view
- [ ] Show real-time progress

---

## 🔧 **Implementation Plan**

### Phase 1: Basic Investigation Page (PRIORITY)
1. Create `/ui/src/app/investigation/page.tsx`
2. Add simple file upload form
3. Add job creation button
4. Display job ID after creation
5. Link from "Start Guided Investigation" button

### Phase 2: File Upload Enhancement
1. Create `/ui/src/components/investigation/FileUpload.tsx`
2. Add drag-and-drop functionality
3. Add file validation
4. Show upload progress
5. Display uploaded files list

### Phase 3: Streaming Interface
1. Create `/ui/src/components/investigation/StreamingChat.tsx`
2. Implement SSE connection
3. Display real-time updates
4. Show conversation turns
5. Add status indicators

### Phase 4: Full Integration
1. Connect all components
2. Add error handling
3. Add loading states
4. Polish UI/UX
5. Test end-to-end workflow

---

## 📖 **Backend API Reference**

### Job Creation
```typescript
POST /api/jobs
Body: {
  user_id: string,
  job_type: "rca_analysis",
  input_manifest: {},
  provider: "ollama",
  model: "llama2",
  priority: 0
}
Response: JobResponse with job.id
```

### File Upload
```typescript
POST /api/files/upload
Content-Type: multipart/form-data
Body:
  - file: File
  - job_id: UUID (optional, can add later)
Response: {
  id: string,
  filename: string,
  content_type: string,
  size: number
}
```

### Streaming
```typescript
GET /api/jobs/{job_id}/stream
Response: SSE stream
Events:
  - status_change
  - progress_update
  - turn_created
  - completed
  - error
```

---

## 🚀 **Quick Fix Action Items**

### Immediate (Fix Button):
1. Update `handleStartInvestigation` in `tickets/page.tsx` to route to `/investigation`
2. Create basic `/investigation` page with placeholder
3. Add "Coming Soon" or basic form

### Short-term (Critical Features):
1. Implement file upload component
2. Implement job creation flow
3. Add basic streaming display

### Medium-term (Full Experience):
1. Polish streaming interface
2. Add conversation history
3. Add file management
4. Improve error handling

---

## 💡 **Notes**

### Why This Is Critical:
- **Core functionality is missing** - users can't actually USE the RCA engine
- The UI is currently **read-only** - just showing preview/demo data
- **"Start Guided Investigation" button is misleading** - does nothing useful
- Backend is fully functional, UI just needs to connect to it

### User Impact:
- Users can't upload files for analysis
- Users can't create new investigations
- Users can't see live updates
- Application appears broken/incomplete

### Technical Debt:
- Current UI is a "showcase" not a "working app"
- Need to bridge gap between backend capabilities and frontend
- SSE integration is standard but needs implementation
- File upload is standard multipart/form-data

---

## 📚 **References**

- Backend API: See `README.md` for full API documentation
- Jobs Router: `apps/api/routers/jobs.py`
- Files Router: `apps/api/routers/files.py`
- SSE Router: `apps/api/routers/sse.py`
- Job Service: `core/jobs/service.py`

---

**Status:** 🔴 CRITICAL - Core functionality missing
**Priority:** P0 - Blocks all user workflows
**Complexity:** Medium - Standard web patterns (file upload + SSE)
**Estimated Effort:** 2-3 days for full implementation
