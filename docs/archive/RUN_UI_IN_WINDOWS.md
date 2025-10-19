# Running UI in Windows (Not Docker)

This guide shows you how to run the **frontend UI directly in Windows** while keeping the backend services in Docker/WSL.

## Benefits

✅ **Faster hot-reload** - changes appear instantly  
✅ **Better debugging** - use browser DevTools directly  
✅ **No network issues** - no WSL networking problems  
✅ **Easy development** - edit and see changes immediately  

---

## Prerequisites

Make sure you have **Node.js** installed on Windows:
- Download from: https://nodejs.org/
- Recommended: Node.js 18.x or 20.x LTS
- Verify installation: `node --version` and `npm --version`

---

## Quick Start

### Step 1: Start Backend Services Only

Run the backend services in Docker (without the UI container):

```batch
start-backend-only.bat
```

This starts:
- ✅ PostgreSQL Database (port 15432)
- ✅ Redis (port 6379) 
- ✅ Ollama LLM (port 11434)
- ✅ API Backend (port 8000)

Wait for services to be healthy (~30 seconds).

### Step 2: Start UI in Windows

In a **new terminal**, run:

```batch
start-ui-windows.bat
```

This will:
1. Install dependencies (first time only - may take 2-3 minutes)
2. Start the Next.js dev server
3. Open your browser to http://localhost:3000

**That's it!** 🎉

---

## Manual Setup (Alternative)

If you prefer to run commands manually:

### 1. Stop the Docker UI container (if running)

```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml stop ui"
```

### 2. Start backend services

```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d rca_core rca_db redis ollama"
```

### 3. Set up port forwarding (if needed)

If you can't access http://localhost:8000, run:

```batch
setup-network.bat
```

Right-click → "Run as administrator"

### 4. Install UI dependencies

```powershell
cd ui
npm install
```

### 5. Create environment file

Create `ui\.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NODE_ENV=development
```

### 6. Start the UI

```powershell
cd ui
npm run dev
```

---

## Accessing the Application

Once everything is running:

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8001/metrics

---

## Development Workflow

### Making Changes to the UI

1. Edit files in `ui/src/`
2. Save the file
3. Browser automatically refreshes (hot reload)

### Making Changes to the Backend

1. Edit files in `apps/`, `core/`, etc.
2. Restart the API container:
   ```powershell
   wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart rca_core"
   ```

---

## Troubleshooting

### UI won't start - "Cannot find module 'next'"

```powershell
cd ui
rm -rf node_modules package-lock.json
npm install
```

### UI can't connect to API

1. Verify API is running:
   ```powershell
   curl http://localhost:8000/api/health/live
   ```

2. Check `.env.local` has correct API URL:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Restart the UI dev server

### Port 3000 already in use

Stop the Docker UI container:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml stop ui"
```

Or use a different port:
```powershell
cd ui
npm run dev -- -p 3001
```

### Backend not accessible from Windows

Run the network setup script:
```batch
setup-network.bat
```

Right-click → "Run as administrator"

---

## Stopping Everything

### Stop UI (Windows)
Press `Ctrl+C` in the terminal running the UI

### Stop Backend Services
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down"
```

Or use the shortcut:
```batch
stop-all.bat
```

---

## Going Back to Full Docker Setup

To run everything in Docker again:

```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml up -d"
```

This will start all services including the UI container.

---

## Tips

💡 **Keep the terminal open** - Don't close the terminal running `npm run dev`  
💡 **Use VS Code terminal** - Easier to manage multiple terminals  
💡 **Check both services** - Make sure both backend (8000) and frontend (3000) are running  
💡 **Hot reload** - Most changes appear instantly without restart  
💡 **Check console** - Browser console shows any API connection errors  

---

## Need Help?

Check the logs:

**UI logs**: Check the terminal running `npm run dev`  
**API logs**: 
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml logs -f rca_core"
```
