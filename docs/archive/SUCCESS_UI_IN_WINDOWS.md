# ✅ SUCCESS! RCA Engine Running in Windows

## Current Setup

Your RCA Engine is now running with:

**Frontend (UI)**: Running natively in Windows  
- URL: http://localhost:3000
- Location: `ui/` directory
- Running via: `npm run dev`
- ✅ Hot reload enabled - changes appear instantly!

**Backend (API)**: Running in Docker/WSL  
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs
- Running via: Docker Compose

**Database & Services**: Running in Docker/WSL
- PostgreSQL: localhost:15432
- Redis: (internal)
- Ollama: (internal)

---

## What We Fixed

1. ❌ **Problem**: WSL networking was blocking Windows → WSL connections
2. ❌ **Problem**: Docker UI container couldn't be accessed from Windows
3. ✅ **Solution**: Run UI directly in Windows (no Docker needed!)
4. ✅ **Solution**: Killed Python process that was blocking port 8000

---

## How to Use

### Start Everything

**Terminal 1**: Backend is already running in Docker  
Check status: `wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml ps"`

**Terminal 2**: UI is already running  
Check the terminal where you ran `npm run dev` - it should show "✓ Ready"

### Stop Everything

**Stop UI**: Press `Ctrl+C` in the terminal running the UI

**Stop Backend**:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down"
```

### Restart After Reboot

1. Start backend: `.\start-backend-only.bat` (or use Docker commands)
2. Start UI: `.\start-ui-windows.bat` (or `cd ui && npm run dev`)

---

## Development Workflow

### Making UI Changes

1. Edit files in `ui/src/`
2. Save
3. Browser auto-refreshes! ✨

No need to restart anything!

### Making Backend Changes

1. Edit files in `apps/`, `core/`, etc.
2. Restart backend:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart rca_core"
```

---

## Batch Files Created

**`start-ui-windows.bat`** - Start UI in Windows (auto-installs dependencies)  
**`start-backend-only.bat`** - Start only backend services in Docker  
**`quick-start-backend.bat`** - Restart Docker and start backend  
**`setup-network.bat`** - Set up port forwarding (if needed)  
**`cleanup-network.bat`** - Remove port forwarding rules

---

## Troubleshooting

### UI won't start

```powershell
cd ui
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend not accessible

Check if it's running:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml logs rca_core"
```

Restart it:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml restart rca_core"
```

### Port 8000 already in use

Find and kill the process:
```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Port 3000 already in use

Stop the Docker UI container:
```powershell
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml stop ui"
```

---

## Benefits of This Setup

✅ **Fast hot-reload** - UI changes appear instantly  
✅ **Better debugging** - Use Chrome DevTools directly  
✅ **No networking issues** - Everything runs on localhost  
✅ **Easy development** - Native Windows tools work perfectly  
✅ **Backend isolation** - API runs in Docker for consistency  

---

## Access URLs

- **UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health/live
- **Metrics**: http://localhost:8001/metrics

---

## Next Steps

1. **Open http://localhost:3000** in your browser
2. **Start developing!** Edit files in `ui/src/`
3. **Check the terminal** where `npm run dev` is running for any errors
4. **View API docs** at http://localhost:8000/docs

---

## Need Help?

- **UI Logs**: Check the terminal running `npm run dev`
- **Backend Logs**: `wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml logs -f rca_core"`
- **Database**: Connect to localhost:15432 with user `rca_user`

🎉 **Happy coding!**
