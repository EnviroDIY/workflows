@echo off
REM Windows batch script for running the CI Build Pipeline locally
REM Equivalent to the bash script in CI_BUILD_PIPELINE.md

call conda activate pio_ci_test

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Set up workspace directory (current working directory is expected to be the repository root)
set WORKSPACE_DIR=%cd%

REM Enable debug mode if RUNNER_DEBUG is set
if defined RUNNER_DEBUG (
    echo [DEBUG] Script directory: %SCRIPT_DIR%
    echo [DEBUG] Workspace directory: %WORKSPACE_DIR%
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

echo.
echo ============================================
echo CI Build Pipeline - Local Execution
echo ============================================
echo.

REM Step 0: Download utilities
echo [Step 0] Downloading matrix_utils.py...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/matrix_utils.py" "matrix_utils.py"
if errorlevel 1 goto :error

REM Step 0a: Download and run 0_setup_ci_platforms.py
echo.
echo [Step 0a] Downloading and running 0_setup_ci_platforms.py...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/0_setup_ci_platforms.py" "0_setup_ci_platforms.py"
if errorlevel 1 goto :error

python 0_setup_ci_platforms.py
if errorlevel 1 (
    echo Error: 0_setup_ci_platforms.py failed with exit code !errorlevel!
    goto :error
)

REM Step 0b: Download and run 0_generate_install_scripts.py
echo.
echo [Step 0b] Downloading and running 0_generate_install_scripts.py...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/0_generate_install_scripts.py" "0_generate_install_scripts.py"
if errorlevel 1 goto :error

python 0_generate_install_scripts.py
if errorlevel 1 (
    echo Error: 0_generate_install_scripts.py failed with exit code !errorlevel!
    goto :error
)

REM Step 1: Download pipeline scripts
echo.
echo [Step 1] Downloading pipeline scripts 1-6...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/1_configure_matrix.py" "1_configure_matrix.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/2_parse_inputs.py" "2_parse_inputs.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/3_build_matrix.py" "3_build_matrix.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/4_build_jobs.py" "4_build_jobs.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/5_output_results.py" "5_output_results.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/6_cleanup.py" "6_cleanup.py"
if errorlevel 1 goto :error

REM Step 2: Run pipeline scripts in sequence
echo.
echo [Step 2] Running pipeline scripts...

echo.
echo Running 1_configure_matrix.py...
python 1_configure_matrix.py
if errorlevel 1 (
    echo Error: 1_configure_matrix.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 2_parse_inputs.py...
python 2_parse_inputs.py
if errorlevel 1 (
    echo Error: 2_parse_inputs.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 3_build_matrix.py...
python 3_build_matrix.py
if errorlevel 1 (
    echo Error: 3_build_matrix.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 4_build_jobs.py...
python 4_build_jobs.py
if errorlevel 1 (
    echo Error: 4_build_jobs.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 5_output_results.py...
python 5_output_results.py
if errorlevel 1 (
    echo Error: 5_output_results.py failed with exit code !errorlevel!
    goto :error
)

REM Step 3: Run cleanup (only runs locally, not in GitHub Actions)
echo.
echo [Step 3] Running cleanup script...
python 6_cleanup.py
if errorlevel 1 (
    echo Warning: 6_cleanup.py failed with exit code !errorlevel!
    REM Don't exit on cleanup failure
)

echo.
echo ============================================
echo CI Build Pipeline - Completed Successfully
echo ============================================
echo.
goto :end

:download_file
setlocal
set URL=%~1
set FILENAME=%~2

if defined RUNNER_DEBUG (
    echo [DEBUG] Downloading: %URL%
    echo [DEBUG] Saving as: %FILENAME%
)

REM Use PowerShell to download the file
powershell -NoProfile -Command ^
    try { ^
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; ^
        Invoke-WebRequest -Uri '%URL%' -OutFile '%FILENAME%' -ErrorAction Stop; ^
        exit 0 ^
    } catch { ^
        Write-Error $_.Exception.Message; ^
        exit 1 ^
    }

if errorlevel 1 (
    echo Error: Failed to download %FILENAME% from %URL%
    endlocal
    exit /b 1
)

endlocal
exit /b 0

:error
echo.
echo ============================================
echo CI Build Pipeline - FAILED
echo ============================================
echo.
exit /b 1

:end
endlocal
