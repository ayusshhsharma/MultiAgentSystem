# ============================================================
# MultiAgentSystem - Live Demo One-Command Launcher
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Activate .venv if present
if (Test-Path "$ScriptDir\.venv\Scripts\Activate.ps1") {
    $env:PATH = "$ScriptDir\.venv\Scripts;$env:PATH"
    & "$ScriptDir\.venv\Scripts\Activate.ps1"
}

# 2. Run preflight check
python preflight.py

# 3. Launch Streamlit UI
Write-Host "`nLaunching Streamlit web dashboard..." -ForegroundColor Green
streamlit run app.py
