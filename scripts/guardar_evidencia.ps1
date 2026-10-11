# Uso (PowerShell, desde la raiz, con el venv activo):  .\scripts\guardar_evidencia.ps1 inc-002
param([string]$Carpeta = "inc-002")
New-Item -ItemType Directory -Force "evidence\$Carpeta" | Out-Null
pytest -v 2>&1 | Tee-Object "evidence\$Carpeta\pytest-final.txt"
