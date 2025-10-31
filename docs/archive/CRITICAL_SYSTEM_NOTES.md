# ⚠️ CRITICAL SYSTEM NOTES - MUST READ

## 🚨 Docker/WSL Requirement

**NEVER run Docker commands directly from Windows PowerShell/CMD!**

### ❌ WRONG (Will Fail):
```powershell
docker ps
docker compose up
python -m uvicorn apps.api.main:app --port 8000
```

### ✅ CORRECT (Always Use WSL):
```powershell
# Use the provided scripts:
.\quick-start-backend.bat

# Or run via WSL:
wsl bash -c "docker ps"
wsl bash -c "docker compose -f deploy/docker/docker-compose.yml up -d"
```

**Why?** This project uses Docker through WSL, not Docker Desktop on Windows directly.

---

## 🎯 Quick Start Commands

### Start Everything
```powershell
# 1. Start Backend (via WSL):
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\quick-start-backend.bat

# 2. Wait 15-20 seconds, then verify:
wsl bash -c "docker ps"

# 3. Start UI:
.\start-ui-windows.bat
```

### Check Status
```powershell
# Backend containers (via WSL):
wsl bash -c "docker ps --filter 'name=rca'"

# Backend logs:
wsl bash -c "docker logs rca_core --tail 50"

# Test API:
curl http://localhost:8000/docs
```

### Stop Services
```powershell
# Stop backend (via WSL):
wsl bash -c "cd /mnt/c/Users/syed.shareef/.vscode/repos/RCA\ -\ v7/RCA-Final && docker compose -f deploy/docker/docker-compose.yml down"

# Stop UI:
# Press Ctrl+C in the UI terminal
```

---

## 📋 Validation Features Implemented

### Sign Up Form Now Has:

1. **Email Validation**
   - Format check: `user@domain.com`
   - Duplicate check on server
   - Clear error messages

2. **Username Validation**
   - 3-50 characters
   - Alphanumeric + underscore + hyphen only
   - Duplicate check on server

3. **Password Validation (Real-Time Visual)**
   - ✓/✗ At least 8 characters
   - ✓/✗ One uppercase letter
   - ✓/✗ One lowercase letter
   - ✓/✗ One number
   - **Live checklist updates as you type!**

4. **Clear Error Messages**
   - "This email is already registered..."
   - "This username is already taken..."
   - "Password must contain at least one uppercase letter"
   - Etc.

---

## 🧪 How to Test Validation

### Test Password Visual Feedback:
1. Go to http://localhost:3000 or 3001
2. Click **"Sign Up"**
3. Start typing in password field
4. **Watch the checkmarks turn green as you meet requirements!**

Example: Type `TestPass123`
- After `T`: uppercase ✓ turns green
- After `Te`: lowercase ✓ turns green  
- After `Test1`: number ✓ turns green
- After `TestPass123`: length ✓ turns green
- **All green = valid password!**

### Test Error Messages:
- Try invalid email: `notanemail` → Error
- Try short username: `ab` → Error
- Try weak password: `pass` → See red X marks
- Try duplicate registration → Clear error message

---

## 📁 Important Files

### Must Read:
- `IMPORTANT_DOCKER_SETUP.md` - WSL/Docker requirements
- `SIGNUP_VALIDATION_COMPLETE.md` - Full test scenarios

### Reference:
- `AUTHENTICATION_GUIDE.md` - Auth system overview
- `WSL_NETWORKING_FIX.md` - Network troubleshooting
- `WSL_QUICKSTART.md` - WSL setup

### Code:
- `ui/src/app/page.tsx` - Signup form with validation

---

## 🎯 URLs

- **UI**: http://localhost:3000 or http://localhost:3001
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8001/metrics

---

## 🐛 Common Issues

### "Registration failed" - Generic error
**Cause**: Backend not running  
**Fix**: Check Docker via WSL: `wsl bash -c "docker ps"`

### "Sign in to Docker Desktop"
**Cause**: Ran Docker from Windows PowerShell  
**Fix**: Always use WSL! See `IMPORTANT_DOCKER_SETUP.md`

### UI not showing validation
**Cause**: Old code cached  
**Fix**: Hard refresh: `Ctrl + Shift + R`

### Backend not responding
**Cause**: Still starting up (takes 15-30 seconds)  
**Fix**: Check logs: `wsl bash -c "docker logs rca_core"`

---

## ✅ Checklist Before Testing

- [ ] Read `IMPORTANT_DOCKER_SETUP.md`
- [ ] Started backend via WSL: `.\quick-start-backend.bat`
- [ ] Verified containers running: `wsl bash -c "docker ps"`
- [ ] Waited 15-20 seconds for startup
- [ ] Tested API: `curl http://localhost:8000/docs`
- [ ] Started UI: `.\start-ui-windows.bat`
- [ ] Opened browser: http://localhost:3000 or 3001
- [ ] Clicked "Sign Up" button
- [ ] Tested password validation (watch checkmarks!)

---

**Last Updated**: October 13, 2025

**Status**: ✅ Complete - All validation implemented and documented

**Remember**: ALWAYS use Docker via WSL, NEVER from Windows PowerShell directly!
