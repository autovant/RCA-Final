# ⚡ RCA Engine - ULTRA-SIMPLE Startup Guide

## 🎯 TL;DR - Start Everything

### First Time Only (Run as Administrator):
```powershell
.\ENABLE-NETWORK-ACCESS.ps1
```

### Every Time:
```powershell
.\START-SIMPLE.ps1
```

**That's it!** Opens browser automatically in ~30 seconds.

---

## 🎬 What Happens

1. **Starts Docker** (Backend + Database) - 20 seconds
2. **Starts UI** (New window, native Node) - 10 seconds  
3. **Opens Browser** - http://localhost:3000 (auto-falls back to http://localhost:3001 if 3000 is busy)

---

## 🛑 Stop Everything

```powershell
.\STOP-SIMPLE.ps1
```

Close the UI window (or press Ctrl+C in it).

---

## 📊 Architecture (Simplified)

```
Windows Native:
├── UI (Next.js) → Port 3000 ✅ FAST hot reload

Docker/WSL:
├── Backend (FastAPI) → Port 8000
├── Database (PostgreSQL) → Port 15432
├── Redis (Cache)
└── Ollama (LLM)
```

---

## ⏱️ Performance

| Action | Time |
|--------|------|
| **Full startup** | 30 seconds |
| **UI hot reload** | 50ms (instant!) |
| **Backend restart** | 30 seconds |

---

## 🐛 Troubleshooting

### "Docker Desktop is not running"
Start Docker Desktop from Windows Start menu.

### "Port 8000 already in use"
```powershell
.\STOP-SIMPLE.ps1
.\START-SIMPLE.ps1
```

### "UI shows unstyled page"
1. Close UI window (Ctrl+C)
2. UI will restart automatically or run `.\START-SIMPLE.ps1` again

### "Cannot connect to backend"
Wait 30 seconds for Docker to fully start, then refresh browser.

---

## 📝 Creating an Account

1. Go to http://localhost:3000
2. Click "Sign Up"
3. Fill in:
   - Email
   - Username  
   - Full Name
   - Password (8+ chars, uppercase, lowercase, number)
4. Click "Create Account"

---

## 🎓 For Advanced Users

Want to run backend natively for faster restart?
- See `DEV_SETUP_SIMPLIFIED.md`
- Requires: Visual C++ Build Tools
- Benefit: 2-second backend restart vs 30 seconds

For now, this simple setup is best for demos!

---

## 🚀 Daily Workflow

### Morning:
```powershell
.\START-SIMPLE.ps1
# Wait ~30 seconds
# Start working!
```

### Evening:
```powershell
.\STOP-SIMPLE.ps1
```

---

## 📂 Important Files

- `START-SIMPLE.ps1` - Start everything
- `STOP-SIMPLE.ps1` - Stop everything
- `deploy/docker/docker-compose.yml` - Production config (don't touch)
- `ui/.env.local` - UI configuration

---

## 🎯 What's Different from Before?

**Before:**
- Complex port forwarding scripts ❌
- Firewall configuration needed ❌
- Multiple terminals to manage ❌
- WSL networking issues ❌

**Now:**
- One command to start ✅
- No port forwarding needed ✅
- Auto-opens in new window ✅
- Just works™ ✅

---

## ✨ Tips

1. **Keep Docker Desktop running** - Uses ~2GB RAM
2. **UI auto-restarts** - Just save files and see changes
3. **Backend logs** - Run: `wsl bash -c "docker logs rca_core -f"`
4. **Database access** - Port 15432, credentials in `.env`

---

**Questions?** Check `DEV_SETUP_SIMPLIFIED.md` for detailed docs.

**Ready?** Run `.\START-SIMPLE.ps1` and you're good to go! 🚀
