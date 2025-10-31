$env:RESET_DB_STATE = "true"
.\start-dev.ps1
$env:RESET_DB_STATE = $null  # optional cleanup