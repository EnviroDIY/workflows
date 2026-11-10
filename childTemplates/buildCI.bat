@echo off
setlocal

set "WORKFLOW_SCRIPTS_PATH=C:\Users\sdamiano\Documents\GitHub\EnviroDIY\workflows\build_scripts"

call conda activate arduino_pio
if errorlevel 1 (
    echo Error: Failed to activate the arduino_pio conda environment.
    exit /b 1
)

python -u "%WORKFLOW_SCRIPTS_PATH%\load_ci_workflow.py" ^
    "%~dp0.github\workflows\build_examples.yaml" ^
    "%WORKFLOW_SCRIPTS_PATH%\run_CI_pipeline.bat" ^
    %*
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
