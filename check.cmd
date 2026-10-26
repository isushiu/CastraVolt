@echo off
setlocal
pushd "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo Install uv: https://docs.astral.sh/uv/getting-started/installation/
  popd
  exit /b 1
)
uv run --no-project --python 3.12 scripts\dev.py check
set "result=%errorlevel%"
popd
exit /b %result%
