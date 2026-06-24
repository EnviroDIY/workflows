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

@REM Generate Arduino keywords using doxygen2keywords.xsl and Saxon
echo Converting the Doxygen output to an Arduino keywords file
java -jar "C:\Users\sdamiano\Downloads\SaxonHE12-4J\saxon-he-12.4.jar" -o:"%GITHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\keywords.txt" -s:"%GITHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%_Doxygen\xml\index.xml" -xsl:"%GITHUB_BASE_DIR%\EnviroDIY\workflows\docs\doxygen2keywords.xsl"
@REM perl -i -ne 'print if ! $x{$_}++' "%GITHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%\keywords.txt"

cd "%GITHUB_BASE_DIR%\EnviroDIY\%GITHUB_REPOSITORY%"
