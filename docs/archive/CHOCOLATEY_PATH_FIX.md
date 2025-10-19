# Quick Fix: Chocolatey PATH Issue

## Problem
Chocolatey is installed at `C:\ProgramData\chocolatey` but the `choco` command isn't available in the current PowerShell session.

## Solution

**Close this PowerShell window and open a NEW PowerShell window**, then run:

```powershell
cd "C:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\setup-local-windows.ps1
```

## Why?
Windows adds Chocolatey to the system PATH during installation, but existing PowerShell sessions don't automatically reload environment variables. A fresh PowerShell session will have the updated PATH.

## Alternative: Manual Refresh (if you don't want to close the window)
```powershell
$env:ChocolateyInstall = Convert-Path "$((Get-Command choco -ErrorAction SilentlyContinue).Source)\..\.."
Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1"
refreshenv
```

Then run:
```powershell
.\setup-local-windows.ps1
```

## What the Script Will Do
Once Chocolatey works, the script will:
1. ✅ Install PostgreSQL 15 as a Windows service
2. ✅ Install Redis for Windows
3. ✅ Create the RCA database and user
4. ✅ Run database migrations
5. ✅ Configure everything to work natively on Windows

No more Docker port forwarding issues! 🎉
