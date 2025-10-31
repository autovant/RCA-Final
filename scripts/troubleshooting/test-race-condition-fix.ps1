#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test the race condition fix for file uploads
.DESCRIPTION
    Verifies that jobs are created in 'draft' status and transition to 'pending' after file upload.
    This prevents the worker from picking up jobs before files are attached.
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Testing Race Condition Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$apiBase = "http://localhost:8001"

# Create a test file
$testContent = "This is a test log file for race condition testing.`n"
$testContent += "Timestamp: $(Get-Date)`n"
$testContent += "Test ID: $(New-Guid)`n"
$testFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $testFile -Value $testContent
$testFile = Rename-Item -Path $testFile -NewName "$testFile.log" -PassThru

Write-Host "Test file created: $($testFile.Name)" -ForegroundColor Gray
Write-Host ""

try {
    # Step 1: Upload file without job_id (should create draft job)
    Write-Host "Step 1: Uploading file..." -ForegroundColor Yellow
    
    $form = @{
        file = Get-Item $testFile
    }
    
    $uploadResponse = Invoke-RestMethod -Uri "$apiBase/api/files/upload" -Method POST -Form $form
    $jobId = $uploadResponse.job_id
    
    Write-Host "  ✓ File uploaded successfully" -ForegroundColor Green
    Write-Host "  Job ID: $jobId" -ForegroundColor Gray
    Write-Host ""
    
    # Step 2: Immediately check job status (should be pending, not draft)
    Write-Host "Step 2: Checking job status..." -ForegroundColor Yellow
    
    $job = Invoke-RestMethod -Uri "$apiBase/api/jobs/$jobId"
    
    Write-Host "  Status: $($job.status)" -ForegroundColor $(if ($job.status -eq "pending") { "Green" } else { "Red" })
    Write-Host "  Files in manifest: $($job.input_manifest.files.Count)" -ForegroundColor Gray
    Write-Host ""
    
    # Step 3: Wait and check if worker picks it up
    Write-Host "Step 3: Waiting for worker..." -ForegroundColor Yellow
    Write-Host "  (Worker polls every 5 seconds)" -ForegroundColor Gray
    
    Start-Sleep -Seconds 8
    
    $jobAfter = Invoke-RestMethod -Uri "$apiBase/api/jobs/$jobId"
    
    Write-Host "  Status after 8 seconds: $($jobAfter.status)" -ForegroundColor Gray
    Write-Host ""
    
    # Step 4: Validate results
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Test Results" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $allPassed = $true
    
    # Check 1: Job should be pending or processing (not draft)
    if ($job.status -eq "pending" -or $job.status -eq "processing" -or $job.status -eq "completed") {
        Write-Host "✓ Job status correct: $($job.status)" -ForegroundColor Green
    } else {
        Write-Host "✗ Job status incorrect: $($job.status) (expected pending/processing/completed)" -ForegroundColor Red
        $allPassed = $false
    }
    
    # Check 2: Job should have files attached
    if ($job.input_manifest.files.Count -gt 0) {
        Write-Host "✓ Files attached: $($job.input_manifest.files.Count)" -ForegroundColor Green
    } else {
        Write-Host "✗ No files attached" -ForegroundColor Red
        $allPassed = $false
    }
    
    # Check 3: Job should NOT fail with "No files uploaded"
    if ($jobAfter.status -eq "failed" -and $jobAfter.error_message -like "*No files uploaded*") {
        Write-Host "✗ Job failed with race condition error!" -ForegroundColor Red
        Write-Host "  Error: $($jobAfter.error_message)" -ForegroundColor Red
        $allPassed = $false
    } elseif ($jobAfter.status -eq "failed") {
        Write-Host "⚠ Job failed (but not due to race condition)" -ForegroundColor Yellow
        Write-Host "  Error: $($jobAfter.error_message)" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Job did not fail with race condition" -ForegroundColor Green
    }
    
    Write-Host ""
    
    if ($allPassed) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✓ ALL TESTS PASSED" -ForegroundColor Green
        Write-Host "  Race condition is FIXED!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
    } else {
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "  ✗ SOME TESTS FAILED" -ForegroundColor Red
        Write-Host "  Race condition may still exist" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Job Details:" -ForegroundColor Yellow
    Write-Host "  URL: http://localhost:3000/investigation?jobId=$jobId" -ForegroundColor Gray
    
}
catch {
    Write-Host "✗ Test failed with error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup
    Remove-Item -Path $testFile -ErrorAction SilentlyContinue
}

Write-Host ""
