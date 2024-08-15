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
FOR /F "tokens=1-10 delims=\" %%G IN ("%CURRENT_DIR%") DO echo %%G %%H %%I %%J %%K %%L %%M %%N %%O %%P & set GIBHUB_BASE_DIR=%%G\%%H\%%I\%%J\%%K
echo GitHub Orgs Directory: %GIBHUB_BASE_DIR%

@REM IF "%~1"=="" (
@REM     exit 1
@REM )
@REM set GITHUB_REPOSITORY=%~1

@REM Set directory links
set MCSS_DIR=%GIBHUB_BASE_DIR%\SRGDamia1\m.css\
set REPO_DIR=%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%
set WORKFLOW_DIR=%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\

@REM Delete any old versions of the documentation and css
del "%REPO_DIR%_Doxygen\html" /q
del "%REPO_DIR%_Doxygen\xml" /q
del "%REPO_DIR%_Doxygen\m.css" /q
del "%REPO_DIR%\docs\css" /q

@REM Clear out output files
echo "" > "%REPO_DIR%\docs\output_generateLogo.log"
echo "" > "%REPO_DIR%\docs\output_documentExamples.log"
echo "" > "%REPO_DIR%\docs\output_doxygen_run.log"
echo "" > "%REPO_DIR%\docs\output_doxygen.log"
echo "" > "%REPO_DIR%\docs\output_fixSectionsInXml.log"
echo "" > "%REPO_DIR%\docs\output_fixFunctionsInGroups.log"
echo "" > "%REPO_DIR%\docs\output_mcss_run.log"
echo "" > "%REPO_DIR%\docs\output_mcss.log"
echo "" > "%REPO_DIR%\docs\output_copyFunctions.log"
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
@REM  download the markdown pre-filter
copy "%WORKFLOW_DIR%markdown_prefilter.py" "%REPO_DIR%\docs"

@REM Document the examples from the header of each example
echo Creating dox files from example file headers
python -u "%WORKFLOW_DIR%documentExamples.py" > output_documentExamples.log 2>&1

@REM Set global vars for local work, then run Doxygen
setlocal
set PLATFORMIO_GLOBALLIB_DIR=../.pio/libdeps/mayfly
set PLATFORMIO_PACKAGES_DIR=C:/Users/sdamiano/.platformio/PLATFORMIO_PACKAGES_DIR

echo Generating Doxygen code documentation...
"C:\Program Files\doxygen\bin\doxygen.exe" Doxyfile > output_doxygen_run.log 2>&1
@REM "C:\Program Files\doxygen\bin\doxygen.exe" -d filteroutput -d commentcnv -d markdown Doxyfile > output_doxygen_run.log 2>&1
endlocal

@REM Fix up xml sections before running m.css
echo Fixing errant xml section names in examples as generated by Doxygen...
python -u "%WORKFLOW_DIR%fixSectionsInXml.py" > output_fixSectionsInXml.log 2>&1

@REM echo Fixing copied function documentation in group documentation
@REM python -u fixFunctionsInGroups.py > output_fixFunctionsInGroups.log 2>&1

@REM Run m.css
echo Running m.css Doxygen post-processor...
python -u "%MCSS_DIR%documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss.log --templates "%MCSS_DIR%documentation\templates\EnviroDIY" --debug > output_mcss_run.log 2>&1
@REM python -u "%MCSS_DIR%documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss.log --templates "%MCSS_DIR%documentation\templates\EnviroDIY" > output_mcss_run.log 2>&1

@REM copy functions so they look right
echo Copying function documentation
python -u "%WORKFLOW_DIR%copyFunctions.py" > output_copyFunctions.log 2>&1

IF "%GITHUB_REPOSITORY%"=="ModularSensors" (
  echo Checking for inclusion of all ModularSensors components
  cd "%REPO_DIR%\continuous_integration"
  python -u check_component_inclusion.py > output_check_component_inclusion.log 2>&1
)

@REM Delete copied files
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
