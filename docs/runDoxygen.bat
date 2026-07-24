call conda activate doxymcss

@REM The current working directory, will change with cd commands
SET CURRENT_DIR=%cd%

@REM The directory the script was called from (removing last slash character)
set CALLING_DIR=%~dp0
set CALLING_DIR=%CALLING_DIR:~0,-1%

@REM https://stackoverflow.com/questions/17279114/split-path-and-take-last-folder-name-in-batch-script

for %%f in ("%CURRENT_DIR%") do set GITHUB_REPOSITORY=%%~nxf
echo GitHub Repo: %GITHUB_REPOSITORY%

@REM https://stackoverflow.com/questions/26537949/how-to-split-variables-in-batch-files
FOR /F "tokens=1-10 delims=\" %%G IN ("%CURRENT_DIR%") DO echo %%G %%H %%I %%J %%K %%L %%M %%N %%O %%P & set GITHUB_BASE_DIR=%%G\%%H\%%I\%%J\%%K
echo GitHub Orgs Directory: %GITHUB_BASE_DIR%

@REM IF "%~1"=="" (
@REM     exit 1
@REM )
@REM set GITHUB_REPOSITORY=%~1

@REM Set directory links
set MCSS_DIR=%GITHUB_BASE_DIR%\SRGDamia1\m.css\
echo mcss Directory: %MCSS_DIR%
set REPO_DIR=%GITHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%
echo Repository Directory: %REPO_DIR%
set WORKFLOW_DIR=%GITHUB_BASE_DIR%\EnviroDIY\workflows\docs\
echo Workflows Directory: %WORKFLOW_DIR%

@REM Delete any old versions of the documentation and css
echo Deleting any previous documentation directories
del "%REPO_DIR%_Doxygen\html" /q
del "%REPO_DIR%_Doxygen\xml" /q
del "%REPO_DIR%_Doxygen\m.css" /q
del "%REPO_DIR%_Doxygen\sqlite3" /q
del "%REPO_DIR%\docs\css" /q
del "%REPO_DIR%\generated_docs" /q

@REM Clear out output files
echo Clearing content any previous output files
echo "" > "%REPO_DIR%\docs\output_generateLogo.log"
echo "" > "%REPO_DIR%\docs\output_documentExamples.log"
echo "" > "%REPO_DIR%\docs\output_doxygen_run.log"
echo "" > "%REPO_DIR%\docs\output_doxygen.log"
echo "" > "%REPO_DIR%\docs\output_preprocessXML.log"
@REM echo "" > "%REPO_DIR%\docs\output_fixFunctionsInGroups.log"
echo "" > "%REPO_DIR%\docs\output_mcss_run.log"
echo "" > "%REPO_DIR%\docs\output_mcss.log"
echo "" > "%REPO_DIR%\docs\output_moxygen_run.log"
echo "" > "%REPO_DIR%\docs\output_moxygen.log"
echo "" > "%REPO_DIR%\docs\output_copyFunctions.log"
echo "" > "%REPO_DIR%\docs\output_removeStupidLinks.log"
echo "" > "%REPO_DIR%\docs\output_check_component_inclusion.log"

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
cd "%MCSS_DIR%css\EnviroDIY"
@REM pygmentize -f html -S arduino -a ".m-code-arduino" > pygments-arduino.css
@REM pygmentize -f html -S default -a ".m-code-pygments-default" > pygments-default.css
python -u "%MCSS_DIR%css\postprocess.py" "m-EnviroDIY.css" "m-documentation.css" -o "%MCSS_DIR%css/EnviroDIY/m-EnviroDIY+documentation.compiled.css"  2>&1

mkdir "%REPO_DIR%\docs\css"
copy "%MCSS_DIR%css\EnviroDIY\m-EnviroDIY+documentation.compiled.css" "%REPO_DIR%\docs\css"
copy "%MCSS_DIR%documentation\clipboard.js" "%REPO_DIR%\docs"

@REM Move back to the repository directory
cd "%REPO_DIR%"

echo Generating library logos
@REM Download the font and favicon
copy "%WORKFLOW_DIR%Ubuntu-Bold.ttf" "%REPO_DIR%\"
copy "%WORKFLOW_DIR%enviroDIY_Favicon.png" "%REPO_DIR%\docs"
@REM Generate the logos
python -u "%WORKFLOW_DIR%generateLogos.py" > docs\output_generateLogo.log 2>&1

@REM Move back to the docs directory
cd "%REPO_DIR%\docs"

@REM Document the examples from the header of each example
echo Creating dox files from example file headers
python -u "%WORKFLOW_DIR%documentExamples.py" > output_documentExamples.log 2>&1

@REM  download the markdown pre-filter
echo Copying markdown pre-filter to docs directory
copy "%WORKFLOW_DIR%markdown_prefilter.py" "%REPO_DIR%\docs"

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
python -u "%WORKFLOW_DIR%preprocessXML.py" > output_preprocessXML.log 2>&1
IF %errorlevel% NEQ 0 (
  echo xml post-processor failed with error code %errorlevel%.
  exit /b %errorlevel%
)

@REM echo Fixing copied function documentation in group documentation
@REM python -u "%WORKFLOW_DIR%fixFunctionsInGroups.py" > output_fixFunctionsInGroups.log 2>&1
@REM IF %errorlevel% NEQ 0 (
@REM   echo copied function post-processor failed with error code %errorlevel%.
@REM   exit /b %errorlevel%
@REM )

@REM Run m.css
echo Running m.css Doxygen post-processor...
@REM python -u "%MCSS_DIR%documentation\doxygen_markdown.py" "mcss-conf.py" --no-doxygen --output output_mcss_run.log --templates "%MCSS_DIR%documentation\templates\markdown" --debug > output_mcss.log 2>&1
python -u "%MCSS_DIR%documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss_run.log --templates "%MCSS_DIR%documentation\templates\EnviroDIY" --debug > output_mcss.log 2>&1
@REM python -u "%MCSS_DIR%documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss_run.log --templates "%MCSS_DIR%documentation\templates\EnviroDIY" > output_mcss.log 2>&1
IF %errorlevel% NEQ 0 (
  echo m.css post-processor failed with error code %errorlevel%.
  exit /b %errorlevel%
)

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
@REM cd "%REPO_DIR%"

@REM copy functions so they look right
echo Copying function documentation
python -u "%WORKFLOW_DIR%copyFunctions.py" > output_copyFunctions.log 2>&1
IF %errorlevel% NEQ 0 (
  echo copy functions post-processor failed with error code %errorlevel%.
  exit /b %errorlevel%
)

@REM Remove stupid links - to add sub-paging structure you must add pages for every level
@REM and dump links to them in the parent page.
@REM This is to remove those stupid pages and links.
echo Removing stupid links that are created by sub-paging structure
python -u "%WORKFLOW_DIR%removeStupidLinks.py" > output_removeStupidLinks.log 2>&1
IF %errorlevel% NEQ 0 (
  echo stupid link post-processor failed with error code %errorlevel%.
  exit /b %errorlevel%
)

IF "%GITHUB_REPOSITORY%"=="ModularSensors" (
  echo Checking for inclusion of all ModularSensors components
  cd "%REPO_DIR%\continuous_integration"
  python -u check_component_inclusion.py > "%REPO_DIR%\docs\output_check_component_inclusion.log" 2>&1
)
IF %errorlevel% NEQ 0 (
  echo inclusion check failed with error code %errorlevel%.
  exit /b %errorlevel%
)

@REM Run moxygen to generate markdown files from the Doxygen xml output
echo Running moxygen to generate markdown files from the Doxygen xml output
call moxygen --groups --pages --anchors --language cpp --frontmatter --templates "%WORKFLOW_DIR%moxygen_templates" --logfile "%REPO_DIR%\docs\output_moxygen.log" --output "%REPO_DIR%\generated_docs\%%%%s.md" "%REPO_DIR%\..\TinyGSM_Doxygen\xml" > "%REPO_DIR%\docs\output_moxygen_run.log" 2>&1
IF %errorlevel% NEQ 0 (
  echo moxygen post-processor failed with error code %errorlevel%.
  exit /b %errorlevel%
)

@REM Delete copied files
echo Deleting copied files
del "%REPO_DIR%\Ubuntu-Bold.ttf" /q
del "%REPO_DIR%\docs\enviroDIY_favicon.png" /q
del "%REPO_DIR%\docs\gp-desktop-logo.png" /q
del "%REPO_DIR%\docs\gp-mobile-logo.png" /q
del "%REPO_DIR%\docs\gp-scrolling-logo.png" /q
del "%REPO_DIR%\docs\markdown_prefilter.py" /q
del "%REPO_DIR%\docs\examples.dox" /q
del "%REPO_DIR%\docs\clipboard.js" /q
del "%REPO_DIR%\docs\css" /q
rmdir "%REPO_DIR%\docs\css" /q

@REM navigate back to the main directory
cd "%REPO_DIR%"
