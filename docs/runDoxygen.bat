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

@REM Delete any old versions of the documentation and css
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%_Doxygen\html" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%_Doxygen\xml" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%_Doxygen\m.css" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\css" /q

@REM Clear out output files
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_generateLogo.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_documentExamples.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_doxygen_run.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_doxygen.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_fixSectionsInXml.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_fixFunctionsInGroups.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_mcss_run.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_mcss.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_copyFunctions.log"
echo "" > "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\output_check_component_inclusion.log"

@REM Check versions of stuff
echo Current Doxygen version...
"C:\Program Files\doxygen\bin\doxygen.exe" -v
echo Current GraphViz (dot) version...
call dot -V
echo Current TeXLive Version...
call latex --version

@REM Update the style sheets
cd "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\css\EnviroDIY"
echo Update the style sheets
@REM pygmentize -f html -S arduino -a ".m-code-arduino" > pygments-arduino.css
@REM pygmentize -f html -S default -a ".m-code-pygments-default" > pygments-default.css
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\css\postprocess.py" "m-EnviroDIY.css"
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\css\postprocess.py" "m-EnviroDIY.css" "m-documentation.css" -o "m-EnviroDIY+documentation.compiled.css"
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\css\postprocess.py" "m-EnviroDIY.css" "m-theme-EnviroDIY.css" "m-documentation.css" --no-import -o "m-EnviroDIY.documentation.compiled.css"
copy "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\css\EnviroDIY\m-EnviroDIY+documentation.compiled.css" "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\css"
copy "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\documentation\clipboard.js" "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs"

@REM Move back to the repository directory
cd "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%"

echo Generating library logos
@REM Download the font and favicon
copy "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\Ubuntu-Bold.ttf" "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\"
copy "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\enviroDIY_Favicon.png" "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs"
@REM Generate the logos
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\generateLogos.py" > docs\output_generateLogo.log 2>&1

@REM Move back to the docs directory
cd "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs"
@REM  download the markdown pre-filter
copy "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\markdown_prefilter.py" "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs"

@REM echo Creating dox files from example read-me files
@REM C:\Users\sdamiano\AppData\Local\miniconda3\python.exe documentExamples.py > output_documentExamples.log 2>&1

@REM Set global vars for local work, then run Doxygen
setlocal
set PLATFORMIO_GLOBALLIB_DIR=../.pio/libdeps/mayfly
set PLATFORMIO_PACKAGES_DIR=C:/Users/sdamiano/.platformio/PLATFORMIO_PACKAGES_DIR

echo Generating Doxygen code documentation...
@REM "C:\Program Files\doxygen\bin\doxygen.exe" -d markdown Doxyfile > output_doxygen_run.log 2>&1
"C:\Program Files\doxygen\bin\doxygen.exe" Doxyfile > output_doxygen_run.log 2>&1
@REM "C:\Program Files\doxygen\bin\doxygen.exe" Doxyfile
endlocal

@REM Fix up xml sections before running m.css
echo Fixing errant xml section names in examples as generated by Doxygen...
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\fixSectionsInXml.py" > output_fixSectionsInXml.log 2>&1

@REM echo Fixing copied function documentation in group documentation
@REM C:\Users\sdamiano\AppData\Local\miniconda3\python.exe fixFunctionsInGroups.py > output_fixFunctionsInGroups.log 2>&1

@REM Run m.css
echo Running m.css Doxygen post-processor...
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss.log --templates "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\documentation\templates\EnviroDIY" --debug > output_mcss_run.log 2>&1
@REM C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\documentation\doxygen.py" "mcss-conf.py" --no-doxygen --output output_mcss.log --templates "%GIBHUB_BASE_DIR%\SRGDamia1\m.css\documentation\templates\EnviroDIY" > output_mcss_run.log 2>&1

@REM copy functions so they look right
echo Copying function documentation
C:\Users\sdamiano\AppData\Local\miniconda3\python.exe "%GIBHUB_BASE_DIR%\EnviroDIY\workflows\docs\copyFunctions.py" > output_copyFunctions.log 2>&1

IF "%GITHUB_REPOSITORY%"=="ModularSensors" (
  echo Checking for inclusion of all ModularSensors components
  cd "%GIBHUB_BASE_DIR%\EnviroDIY\ModularSensors\continuous_integration"
  C:\Users\sdamiano\AppData\Local\miniconda3\python.exe check_component_inclusion.py > output_check_component_inclusion.log 2>&1
)

@REM Delete copied files
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\Ubuntu-Bold.ttf" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\enviroDIY_favicon.png" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\gp-desktop-logo.png" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\gp-mobile-logo.png" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\gp-scrolling-logo.png" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\markdown_prefilter.py" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\clipboard.js" /q
del "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\docs\css" /q

@REM navigate back to the main directory
cd "%GIBHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%"
