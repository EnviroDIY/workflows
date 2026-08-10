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

REM Set up artifacts directory for downloaded files
set ARTIFACTS_DIR=%WORKSPACE_DIR%\continuous_integration_artifacts
if not exist "%ARTIFACTS_DIR%" mkdir "%ARTIFACTS_DIR%"

@REM https://stackoverflow.com/questions/17279114/split-path-and-take-last-folder-name-in-batch-script

for %%f in ("%WORKSPACE_DIR%") do set GITHUB_REPOSITORY=%%~nxf
echo GitHub Repo: %GITHUB_REPOSITORY%

@REM https://stackoverflow.com/questions/26537949/how-to-split-variables-in-batch-files
FOR /F "tokens=1-10 delims=\" %%G IN ("%WORKSPACE_DIR%") DO echo %%G %%H %%I %%J %%K %%L %%M %%N %%O %%P & set GITHUB_BASE_DIR=%%G\%%H\%%I\%%J\%%K
echo GitHub Orgs Directory: %GITHUB_BASE_DIR%

@REM IF "%~1"=="" (
@REM     exit 1
@REM )
@REM set GITHUB_REPOSITORY=%~1

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
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/matrix_utils.py" "%ARTIFACTS_DIR%\matrix_utils.py"
if errorlevel 1 goto :error

REM Step 1: Download and run configuration scripts
echo.
echo [Step 1] Downloading pipeline scripts 0-2...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/0_configure_workspace.py" "%ARTIFACTS_DIR%\0_configure_workspace.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/1_parse_inputs.py" "%ARTIFACTS_DIR%\1_parse_inputs.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/2_generate_install_scripts.py" "%ARTIFACTS_DIR%\2_generate_install_scripts.py"
if errorlevel 1 goto :error

REM Step 2: Download matrix generation scripts
echo.
echo [Step 2] Downloading pipeline scripts 3-6...
call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/3_build_matrix.py" "%ARTIFACTS_DIR%\3_build_matrix.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/4_build_jobs.py" "%ARTIFACTS_DIR%\4_build_jobs.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/5_output_results.py" "%ARTIFACTS_DIR%\5_output_results.py"
if errorlevel 1 goto :error

call :download_file "https://raw.githubusercontent.com/EnviroDIY/workflows/main/build_scripts/6_cleanup.py" "%ARTIFACTS_DIR%\6_cleanup.py"
if errorlevel 1 goto :error

REM Step 3: Run pipeline scripts in sequence
echo.
echo [Step 3] Running pipeline scripts...

echo.
echo Running 0_configure_workspace.py...
python "%ARTIFACTS_DIR%\0_configure_workspace.py"
if errorlevel 1 (
    echo Error: 0_configure_workspace.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 1_parse_inputs.py...
python "%ARTIFACTS_DIR%\1_parse_inputs.py"
if errorlevel 1 (
    echo Error: 1_parse_inputs.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 2_generate_install_scripts.py...
python "%ARTIFACTS_DIR%\2_generate_install_scripts.py"
if errorlevel 1 (
    echo Error: 2_generate_install_scripts.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 3_build_matrix.py...
python "%ARTIFACTS_DIR%\3_build_matrix.py"
if errorlevel 1 (
    echo Error: 3_build_matrix.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 4_build_jobs.py...
python "%ARTIFACTS_DIR%\4_build_jobs.py"
if errorlevel 1 (
    echo Error: 4_build_jobs.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 5_output_results.py...
python "%ARTIFACTS_DIR%\5_output_results.py"
if errorlevel 1 (
    echo Error: 5_output_results.py failed with exit code !errorlevel!
    goto :error
)

REM Step 4: Run cleanup (only runs locally, not in GitHub Actions, and only if --cleanup argument is provided)
if "%~1"=="--cleanup" (
    echo.
    echo [Step 4] Running cleanup script...
    python "%ARTIFACTS_DIR%\6_cleanup.py"
    if errorlevel 1 (
        echo Warning: 6_cleanup.py failed with exit code !errorlevel!
        REM Don't exit on cleanup failure
    )
) else (
    echo.
    echo [Step 4] Skipping cleanup script (use --cleanup argument to enable)
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
call :cleanup_downloads
exit /b 1

:end
echo.
call :cleanup_downloads
endlocal

:cleanup_downloads
echo Cleaning up downloaded files...
if exist "%ARTIFACTS_DIR%\matrix_utils.py" del "%ARTIFACTS_DIR%\matrix_utils.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\0_configure_workspace.py" del "%ARTIFACTS_DIR%\0_configure_workspace.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\1_parse_inputs.py" del "%ARTIFACTS_DIR%\1_parse_inputs.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\2_generate_install_scripts.py" del "%ARTIFACTS_DIR%\2_generate_install_scripts.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\3_build_matrix.py" del "%ARTIFACTS_DIR%\3_build_matrix.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\4_build_jobs.py" del "%ARTIFACTS_DIR%\4_build_jobs.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\5_output_results.py" del "%ARTIFACTS_DIR%\5_output_results.py" >nul 2>&1
if exist "%ARTIFACTS_DIR%\6_cleanup.py" del "%ARTIFACTS_DIR%\6_cleanup.py" >nul 2>&1
REM Remove the artifacts directory only if it's empty
rmdir "%ARTIFACTS_DIR%" >nul 2>&1
exit /b 0
