@echo off
setlocal

@REM set CI_PATH="C:\your\path\to\ci"
@REM set ARTIFACT_PATH="C:\your\path\to\ci_artifacts"
@REM set EXAMPLES_PATH="C:\your\path\to\examples"
@REM set EXTRAS_PATH="C:\your\path\to\extras"
@REM set CONFIG_FILE_NAME=matrix_config.json
@REM set COMPILER_LIST=arduino-cli,platformio
@REM set EXAMPLES_TO_BUILD=all
@REM set EXAMPLES_TO_IGNORE=
@REM set BOARDS_TO_BUILD=all
@REM set BOARDS_TO_IGNORE=
@REM set ARDUINO_BOARDS_TO_BUILD=all
@REM set ARDUINO_BOARDS_TO_IGNORE=
@REM set PIO_ENVS_TO_BUILD=all
@REM set PIO_ENVS_TO_IGNORE=
@REM set INLINE_DEFINES=
@REM set COMPILER_FLAGS=
@REM set LOG_GROUPING_FIELDS=compiler,board,example,inline_flags
@REM set JOB_GROUPING_FIELDS=compiler,board

call C:\Users\sdamiano\Documents\GitHub\EnviroDIY\workflows\build_scripts\run_CI_pipeline.bat %*

endlocal
