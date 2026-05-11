@echo off
set "PROJ_DIR=%~dp0"
set "PYTHON=%PROJ_DIR%venv\Scripts\python.exe"

echo Starting Chat Server...
start powershell -NoExit -Command "Set-Location -LiteralPath '%PROJ_DIR%'; & '%PYTHON%' -m src.cli.main server --port 9000"

echo Waiting a moment for server to start...
timeout /t 2 /nobreak >nul

echo Starting Alice Client...
start powershell -NoExit -Command "Set-Location -LiteralPath '%PROJ_DIR%'; & '%PYTHON%' -m src.cli.main register --user alice --server localhost:9000; & '%PYTHON%' -m src.cli.main chat --user alice --server localhost:9000"

echo Starting Bob Client...
start powershell -NoExit -Command "Set-Location -LiteralPath '%PROJ_DIR%'; & '%PYTHON%' -m src.cli.main register --user bob --server localhost:9000; & '%PYTHON%' -m src.cli.main chat --user bob --server localhost:9000"
