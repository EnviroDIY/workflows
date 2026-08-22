call conda activate doxymcss

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

@REM Set directory links
set MCSS_DIR=%GITHUB_BASE_DIR%\SRGDamia1\m.css
echo mcss Directory: %MCSS_DIR%

@REM Delete any old versions of the documentation and css
echo Deleting any previous documentation directories
del "%WORKSPACE_DIR%_Doxygen\html" /q
del "%WORKSPACE_DIR%_Doxygen\xml" /q
del "%WORKSPACE_DIR%_Doxygen\m.css" /q
del "%WORKSPACE_DIR%_Doxygen\sqlite3" /q
del "%WORKSPACE_DIR%_Doxygen\md" /q /s
del "%WORKSPACE_DIR%\docs\css" /q
del "%WORKSPACE_DIR%\generated_docs" /q

@REM Clear out output files
echo Clearing content any previous output files
for %%F in (
    output_generateLogo.log
    output_documentExamples.log
    output_doxygen_run.log
    output_doxygen.log
    output_preprocessXML.log
    output_fixFunctionsInGroups.log
    output_mcss_run.log
    output_mcss.log
    output_mcssmd_run.log
    output_mcssmd.log
    output_mcssr.log
    output_mcssr_run.log
    output_moxygen_run.log
    output_moxygen.log
    output_doxybook2_run.log
    output_copyFunctions.log
    output_removeStupidLinks.log
    output_check_component_inclusion.log
) do (
    if exist "%WORKSPACE_DIR%\docs\%%F" (
        del "%WORKSPACE_DIR%\docs\%%F" /q
    )
)

@REM Check versions of stuff
echo Current Doxygen version...
doxygen -v
echo Current GraphViz (dot) version...
call dot -V
echo Current TeXLive Version...
call latex --version
echo Current Python Version...
call python --version

@REM Update the style sheets
echo Update the style sheets
cd "%MCSS_DIR%\css\EnviroDIY"
@REM pygmentize -f html -S arduino -a ".m-code-arduino" > pygments-arduino.css
@REM pygmentize -f html -S default -a ".m-code-pygments-default" > pygments-default.css
python -u "%MCSS_DIR%\css\postprocess.py" "m-EnviroDIY.css" "m-documentation.css" -o "%MCSS_DIR%\css/EnviroDIY/m-EnviroDIY+documentation.compiled.css"  2>&1

mkdir "%WORKSPACE_DIR%\docs\css"
copy "%MCSS_DIR%\css\EnviroDIY\m-EnviroDIY+documentation.compiled.css" "%WORKSPACE_DIR%\docs\css"
copy "%MCSS_DIR%\documentation\clipboard.js" "%WORKSPACE_DIR%\docs"

@REM Move back to the docs directory
cd "%WORKSPACE_DIR%\docs"

echo Generating library logos
@REM Download the font and favicon
copy "%SCRIPT_DIR%\Ubuntu-Bold.ttf" "%WORKSPACE_DIR%\docs"
copy "%SCRIPT_DIR%\enviroDIY_Favicon.png" "%WORKSPACE_DIR%\docs"
@REM Generate the logos
python -u "%SCRIPT_DIR%\generateLogos.py" > output_generateLogo.log 2>&1

@REM Document the examples from the header of each example
echo Creating dox files from example file headers
python -u "%SCRIPT_DIR%\documentExamples.py" > output_documentExamples.log 2>&1

@REM  download the markdown pre-filter
echo Copying markdown pre-filter to docs directory
copy "%SCRIPT_DIR%\markdown_prefilter.py" "%WORKSPACE_DIR%\docs"

@REM Set global vars for local work, then run Doxygen
setlocal
set PLATFORMIO_GLOBALLIB_DIR=../.pio/libdeps/mayfly
set PLATFORMIO_PACKAGES_DIR=C:/Users/sdamiano/.platformio/PLATFORMIO_PACKAGES_DIR

echo Generating Doxygen code documentation...
@REM https://github.com/doxygen/doxygen/blob/master/doc_internal/doxygen.md
"C:\Program Files\doxygen\bin\doxygen.exe" Doxyfile > output_doxygen_run.log 2>&1
@REM "C:\Program Files\doxygen\bin\doxygen.exe" -d preprocessor Doxyfile > output_doxygen_run.log 2>&1
@REM "C:\Program Files\doxygen\bin\doxygen.exe" -d extcmd -d filteroutput -d commentcnv -d markdown Doxyfile > output_doxygen_run.log 2>&1
@REM "C:\Program Files\doxygen\bin\doxygen.exe" -d extcmd -d formula Doxyfile > output_doxygen_run.log 2>&1
endlocal

@REM Preprocess XML to fix bad section ids and anchor ids and remove private functions from the XML output.
echo Preprocessing XML...
python -u "%SCRIPT_DIR%\preprocessXML.py" > output_preprocessXML.log 2>&1
IF %errorlevel% NEQ 0 (
  echo xml post-processor failed with error code %errorlevel%.
  goto :error
)

@REM echo Fixing copied function documentation in group documentation
@REM python -u "%SCRIPT_DIR%\fixFunctionsInGroups.py" > output_fixFunctionsInGroups.log 2>&1
@REM IF %errorlevel% NEQ 0 (
@REM   echo copied function post-processor failed with error code %errorlevel%.
@REM   goto :error
@REM )

@REM Run m.css for html output
echo Running m.css Doxygen post-processor to generate html...
python -u "%MCSS_DIR%\documentation\doxygen.py" "mcss-conf.py" --no-doxygen --debug-template --output output_mcss_run.log --template-type html --templates "%MCSS_DIR%\documentation\templates\EnviroDIY" --debug > output_mcss.log 2>&1
@REM python -u "%MCSS_DIR%\documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss_run.log --templates "%MCSS_DIR%\documentation\templates\EnviroDIY" > output_mcss.log 2>&1
IF %errorlevel% NEQ 0 (
  echo m.css to html post-processor failed with error code %errorlevel%.
  goto :error
)

@REM Run m.css for markdown output
@REM echo Running m.css Doxygen post-processor to generate markdown...
@REM python -u "%MCSS_DIR%\documentation\doxygen.py" "mcss-conf.py" --no-doxygen --debug-template --output output_mcssmd_run.log --template-type md --templates "%MCSS_DIR%\documentation\templates\doxybook2" --debug > output_mcssmd.log 2>&1
@REM python -u "%MCSS_DIR%\documentation\doxygen_refactored.py" "mcss-conf.py" --no-doxygen --format all --debug > output_mcssr.log 2>&1
@REM IF %errorlevel% NEQ 0 (
@REM   echo m.css to markdown post-processor failed with error code %errorlevel%.
@REM   goto :error
@REM )

@REM @REM Move to generated markdown directory to rename files to .md
@REM cd "C:\Users\sdamiano\Documents\GitHub\EnviroDIY\TinyGSM_Doxygen\m.css\"
@REM echo Renaming files to remove ".html" and replace with ".md"
@REM setlocal enabledelayedexpansion
@REM set "search=.html"
@REM set "replace=.md"

@REM for %%F in (*%search%*) do (
@REM set "name=%%F"
@REM ren "!name!" "!name:%search%=%replace%!"
@REM )
@REM endlocal
@REM @REM Move back to the repository directory
@REM cd "%WORKSPACE_DIR%"

@REM copy functions so they look right
echo Copying function documentation
python -u "%SCRIPT_DIR%\copyFunctions.py" > output_copyFunctions.log 2>&1
IF %errorlevel% NEQ 0 (
  echo copy functions post-processor failed with error code %errorlevel%.
  goto :error
)

@REM Remove stupid links - to add sub-paging structure you must add pages for every level
@REM and dump links to them in the parent page.
@REM This is to remove those stupid pages and links.
echo Removing stupid links that are created by sub-paging structure
python -u "%SCRIPT_DIR%\removeStupidLinks.py" > output_removeStupidLinks.log 2>&1
IF %errorlevel% NEQ 0 (
  echo stupid link post-processor failed with error code %errorlevel%.
  goto :error
)

IF "%GITHUB_REPOSITORY%"=="ModularSensors" (
  echo Checking for inclusion of all ModularSensors components
  cd "%WORKSPACE_DIR%\continuous_integration"
  python -u check_component_inclusion.py > "%WORKSPACE_DIR%\docs\output_check_component_inclusion.log" 2>&1
)
IF %errorlevel% NEQ 0 (
  echo inclusion check failed with error code %errorlevel%.
  goto :error
)

@REM @REM Run moxygen to generate markdown files from the Doxygen xml output
@REM echo Running moxygen to generate markdown files from the Doxygen xml output
@REM call moxygen --groups --pages --anchors --language cpp --frontmatter --templates "%SCRIPT_DIR%\moxygen_templates" --logfile "%WORKSPACE_DIR%\docs\output_moxygen.log" --output "%WORKSPACE_DIR%\generated_docs\%%%%s.md" "%WORKSPACE_DIR%\..\TinyGSM_Doxygen\xml" > "%WORKSPACE_DIR%\docs\output_moxygen_run.log" 2>&1
@REM IF %errorlevel% NEQ 0 (
@REM   echo moxygen post-processor failed with error code %errorlevel%.
@REM   goto :error
@REM )

@REM Run doxybook2 to generate markdown files from the Doxygen xml output
echo Running doxybook2 to generate markdown files from the Doxygen xml output
"C:\Program Files\doxybook2\bin\doxybook2.exe" --config "%SCRIPT_DIR%\\.doxybook\config.json" --templates "%SCRIPT_DIR%\\.doxybook\templates" --input "%WORKSPACE_DIR%_Doxygen\xml" --output "%WORKSPACE_DIR%_Doxygen\md" -d > "%WORKSPACE_DIR%\docs\output_doxybook2_run.log" 2>&1
IF %errorlevel% NEQ 0 (
  echo doxybook2 post-processor failed with error code %errorlevel%.
  goto :error
)

echo.
echo ============================================
echo Documentation Build - Completed Successfully
echo ============================================
echo.
goto :end

:error
echo.
echo ============================================
echo Documentation Build - FAILED
echo ============================================
echo.
call :cleanup_downloads
exit /b 1

:end
echo.
call :cleanup_downloads
endlocal

:cleanup_downloads
@REM Delete copied files
echo Deleting copied files
del "%WORKSPACE_DIR%\Ubuntu-Bold.ttf" /q
del "%WORKSPACE_DIR%\docs\Ubuntu-Bold.ttf" /q
del "%WORKSPACE_DIR%\docs\UbuntuMono-Regular.ttf" /q
del "%WORKSPACE_DIR%\docs\main_logo.png" /q
del "%WORKSPACE_DIR%\docs\favicon.png" /q
del "%WORKSPACE_DIR%\docs\enviroDIY_favicon.png" /q
del "%WORKSPACE_DIR%\docs\gp-desktop-logo.png" /q
del "%WORKSPACE_DIR%\docs\gp-mobile-logo.png" /q
del "%WORKSPACE_DIR%\docs\gp-scrolling-logo.png" /q
del "%WORKSPACE_DIR%\docs\markdown_prefilter.py" /q
del "%WORKSPACE_DIR%\docs\examples.dox" /q
del "%WORKSPACE_DIR%\docs\clipboard.js" /q
del "%WORKSPACE_DIR%\docs\css" /q
rmdir "%WORKSPACE_DIR%\docs\css" /q

@REM navigate back to the main directory
cd "%WORKSPACE_DIR%"
