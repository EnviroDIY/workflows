@echo off
setlocal

call conda activate arduino_pio
if errorlevel 1 (
    echo Error: Failed to activate the arduino_pio conda environment.
    exit /b 1
)

python -u "%~dp0load_ci_workflow.py" ^
    "%~dp0.github\workflows\build_examples.yaml" ^
    "C:\Users\sdamiano\Documents\GitHub\EnviroDIY\workflows\build_scripts\run_CI_pipeline.bat" ^
    %*
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
