@echo off
setlocal
pushd "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Please install uv first, then run setup.cmd again.
  popd
  exit /b 1
)
uv run --no-project --python 3.12 scripts\dev.py setup
set "result=%errorlevel%"
popd
exit /b %result%
