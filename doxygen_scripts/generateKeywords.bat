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

@REM Delete old keywords_duplicates file if it exists
if exist "%WORKSPACE_DIR%\keywords_duplicates.txt" (
    echo Deleting old keywords_duplicates file
    del "%WORKSPACE_DIR%\keywords_duplicates.txt" /q
)

@REM Generate Arduino keywords using doxygen2keywords.xsl and Saxon
echo Converting the Doxygen output to an Arduino keywords file
java -jar "%SCRIPT_DIR%\SaxonHE12-10J\saxon-he-12.10.jar" -o:"%WORKSPACE_DIR%\keywords_duplicates.txt" -s:"%WORKSPACE_DIR%_Doxygen\xml\index.xml" -xsl:"%SCRIPT_DIR%\doxygen2keywords.xsl"
if %errorlevel% neq 0 (
    echo Error: Java command failed with exit code %errorlevel%
    exit /b %errorlevel%
)

@REM Delete old keywords file if it exists
if exist "%WORKSPACE_DIR%\keywords.txt" (
    echo Deleting old keywords file
    del "%WORKSPACE_DIR%\keywords.txt" /q
)

@echo off
set "source=%WORKSPACE_DIR%\keywords_duplicates.txt"
set "dest=%WORKSPACE_DIR%\keywords.txt"

powershell -Command "$ErrorActionPreference='Stop'; $h=@{}; Get-Content \"%source%\" | %% { if ($_ -match '^\s*$' -or $_ -match '^\s*#+\s*$') { $_ } elseif (-not $h.ContainsKey($_)) { $h[$_]=$true; $_ } } | Set-Content \"%dest%\""
if %errorlevel% neq 0 (
    echo Error: PowerShell command failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo Duplicates removed. Saved to "%dest%".

echo Deleting file with duplicates
if exist "%WORKSPACE_DIR%\keywords_duplicates.txt" (
    echo Deleting file with duplicates
    del "%WORKSPACE_DIR%\keywords_duplicates.txt" /q
)


cd "%WORKSPACE_DIR%"
