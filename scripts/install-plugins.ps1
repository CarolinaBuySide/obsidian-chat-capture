# Wrapper kept for the old name. The work is done by install_plugins.py.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install-plugins.ps1 "C:\path\to\vault" [--smart-connections] [--obsidian-skills]
$py = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $py (Join-Path $PSScriptRoot "install_plugins.py") @args
exit $LASTEXITCODE
