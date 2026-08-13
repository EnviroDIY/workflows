@echo off
REM Windows batch script for running the CI Build Pipeline locally

call conda activate arduino_pio

setlocal enabledelayedexpansion

REM Set up workspace directory (current working directory is expected to be the repository root)
set WORKSPACE_DIR=%cd%

@REM The directory the script was called from (removing last slash character)
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Set up CI and CI artifacts directory for downloaded files
set CI_DIR=%WORKSPACE_DIR%\continuous_integration
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

@REM Delete any old build artifacts
echo Deleting any previous build artifacts
del "%ARTIFACTS_DIR%" /q

echo.
echo ============================================
echo CI Build Pipeline - Local Execution
echo ============================================
echo.

echo.
echo Running 1_configure_workspace.py...
python -u "%SCRIPT_DIR%\1_configure_workspace.py" %*
if errorlevel 1 (
    echo Error: 1_configure_workspace.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 2_generate_install_scripts.py...
python -u "%SCRIPT_DIR%\2_generate_install_scripts.py" %*
if errorlevel 1 (
    echo Error: 2_generate_install_scripts.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 3_build_matrix.py...
python -u "%SCRIPT_DIR%\3_build_matrix.py" %*
if errorlevel 1 (
    echo Error: 3_build_matrix.py failed with exit code !errorlevel!
    goto :error
)

echo.
echo Running 4_build_jobs.py...
python -u "%SCRIPT_DIR%\4_build_jobs.py" %*
if errorlevel 1 (
    echo Error: 4_build_jobs.py failed with exit code !errorlevel!
    goto :error
)

REM Step 4: Run cleanup (only runs locally, not in GitHub Actions, and only if --cleanup argument is provided)
echo.
echo [Step 4] Running cleanup script...
python -u "%SCRIPT_DIR%\5_cleanup.py" %*
if errorlevel 1 (
    echo Warning: 5_cleanup.py failed with exit code !errorlevel!
    REM Don't exit on cleanup failure
)

echo.
echo ============================================
echo CI Build Pipeline - Completed Successfully
echo ============================================
echo.
goto :end

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
if exist "%CI_DIR%\platformio_to_arduino_boards.json" del "%CI_DIR%\platformio_to_arduino_boards.json" >nul 2>&1
if exist "%CI_DIR%\platformio_platform_tools.json" del "%CI_DIR%\platformio_platform_tools.json" >nul 2>&1
REM Remove the artifacts directory only if it's empty
rmdir "%ARTIFACTS_DIR%" >nul 2>&1
exit /b 0
