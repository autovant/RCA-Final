# RCA Engine - Authentication Guide

## ✅ Sign Up Feature Added!

The UI now includes a **Sign Up** button that allows new users to create accounts.

## How to Get Started

### Option 1: Sign Up via UI (Recommended)

1. **Access the UI**: Open http://localhost:3000 in your browser
2. **Click "Sign Up"**: You'll see a blue "Sign Up" button next to "Log In" in the welcome alert
3. **Fill in the registration form**:
   - **Email**: your.email@company.com
   - **Username**: Choose a username (3-50 characters)
   - **Full Name**: Your full name
   - **Password**: Choose a strong password (minimum 8 characters)
4. **Click "Create Account"**
5. **Automatic redirect**: After successful registration, you'll automatically be redirected to log in

### Option 2: Sign Up via API

If you prefer to use the API directly:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rcaengine.com",
    "username": "admin",
    "password": "SecurePassword123",
    "full_name": "Admin User"
  }'
```

## Login After Registration

Once you've created an account, you can log in:

1. Click the **"Log In"** button
2. Enter your **username** and **password**
3. Click **"Log In"** to access the portal

## UI Features

### Navigation Between Forms

- **Login Modal** → Click "Sign Up" link at the bottom to switch to registration
- **Sign Up Modal** → Click "Log In" link at the bottom to switch to login

### Welcome Alert

The welcome banner now shows both buttons:
- 🔵 **Log In** - For existing users
- ⚪ **Sign Up** - For new users

## Password Requirements

- **Minimum Length**: 8 characters
- **Recommended**: Use a mix of uppercase, lowercase, numbers, and special characters

## Username Requirements

- **Length**: 3-50 characters
- **Format**: Alphanumeric characters and underscores

## Quick Test Account

For testing, you can create a sample account:

**Via UI:**
- Email: `test@example.com`
- Username: `testuser`
- Password: `Test123456`
- Full Name: `Test User`

**Via API:**
```powershell
$body = @{
    email = "test@example.com"
    username = "testuser"
    password = "Test123456"
    full_name = "Test User"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/auth/register" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"
```

## Troubleshooting

### "Registration failed"
- Check if the username or email is already taken
- Ensure password meets minimum length requirement (8 characters)
- Verify the backend API is running on http://localhost:8000

### "Login failed"
- Ensure you're using the correct **username** (not email) to log in
- Double-check your password
- Confirm your account was successfully created

### Backend Not Responding
If you get connection errors:

```powershell
# Check if backend is running
wsl docker ps --filter "name=rca_core"

# Restart backend if needed
cd "c:\Users\syed.shareef\.vscode\repos\RCA - v7\RCA-Final"
.\restart-backend.ps1
```

## API Endpoints

### Registration
- **Endpoint**: `POST /api/auth/register`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "username": "username",
    "password": "password123",
    "full_name": "Full Name"
  }
  ```

### Login
- **Endpoint**: `POST /api/auth/token`
- **Body** (form-data):
  - `username`: your username
  - `password`: your password
- **Response**:
  ```json
  {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer"
  }
  ```

## Next Steps After Login

Once logged in, you can:
- ✅ Create new RCA analysis jobs
- ✅ View job history and status
- ✅ Upload log files for analysis
- ✅ Configure ITSM ticket integration
- ✅ Monitor job events in real-time

---

**Updated**: October 13, 2025
**Feature**: Sign Up functionality added to UI
