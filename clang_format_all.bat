call conda activate arduino_pio

REM Set up workspace directory (current working directory is expected to be the repository root)
SET WORKSPACE_DIR=%cd%
echo Repository Workspace Directory: %WORKSPACE_DIR%

@REM The directory the script was called from (removing last slash character)
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
echo Workflows Directory: %SCRIPT_DIR%

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

python -u "%SCRIPT_DIR%\clang-format-all.py"
