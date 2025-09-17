#!/bin/bash

# Script modified from scripts by Jeroen de Bruijn, thephez, and Adafruit
# https://gist.github.com/vidavidorra/548ffbcdae99d752da02
# https://github.com/thephez/doxygen-travis-build
# https://learn.adafruit.com/the-well-automated-arduino-library/travis-ci

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

# Set directory links
MCSS_DIR=$GITHUB_WORKSPACE/code_docs/m.css/
REPO_DIR=$GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/}
WORKFLOW_DIR=https://raw.githubusercontent.com/EnviroDIY/workflows/main/docs/

# Check versions of stuff
echo -e "\e[36mCurrent Doxygen version...\e[0m"
doxygen -v 2>&1
echo -e "\e[36mCurrent GraphViz (dot) version......\e[0m"
dot -V || true
echo -e "\e[36mCurrent TeXLive Version......\e[0m"
latex --version || true
# list all the TeX Live packages, if debugging is on
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "::group::Installed TeX Live Packages"
    tlmgr info --list --only-installed --data name -V || true
    echo "::endgroup::"
fi
echo -e "\e[36mCurrent Python Version......\e[0m"
python --version

# Update the style sheets
echo "::group::Updating style sheets"
cd ${MCSS_DIR}css/EnviroDIY
# pygmentize -f html -S arduino -a ".m-code-arduino" >pygments-arduino.css
# pygmentize -f html -S default -a ".m-code-pygments-default" >pygments-default.css
python -u "${MCSS_DIR}css/postprocess.py" "m-EnviroDIY.css" "m-documentation.css" -o "${MCSS_DIR}css/EnviroDIY/m-EnviroDIY+documentation.compiled.css"

# list the directory contents if GitHub actions debugging is on
if [ "$RUNNER_DEBUG" = "1" ]; then
    ls ${MCSS_DIR}css/EnviroDIY/ -R
fi

mkdir -p "${REPO_DIR}/docs/css"
cp "${MCSS_DIR}css/EnviroDIY/m-EnviroDIY+documentation.compiled.css" "${REPO_DIR}/docs/css"
cp "${MCSS_DIR}documentation/clipboard.js" "${REPO_DIR}/docs"
echo "::endgroup::"

# Move back to the repository directory
cd "${REPO_DIR}"

echo "::group::Generating library logos"
# Download the font and favicon
curl -SL "${WORKFLOW_DIR}Ubuntu-Bold.ttf" -o Ubuntu-Bold.ttf
curl -SL "${WORKFLOW_DIR}enviroDIY_Favicon.png" -o docs/enviroDIY_Favicon.png
# Download the logo generation script
curl -SL "${WORKFLOW_DIR}generateLogos.py" -o generateLogos.py
# Generate the logos
python -u generateLogos.py 2>&1
echo "::endgroup::"

# Move back to the docs directory
cd ${REPO_DIR}/docs
# download the markdown pre-filter
curl -SL ${WORKFLOW_DIR}markdown_prefilter.py -o markdown_prefilter.py

echo "::group::Listing current directory contents"
echo "Current directory: $PWD"
ls -R
echo "::endgroup::"

if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "::group::Listing contents of $GITHUB_WORKSPACE/code_docs/"
    ls $GITHUB_WORKSPACE/code_docs/
    echo "::endgroup::"

    echo "-------------------"

    echo "::group::Listing contents of ${REPO_DIR} recursively"
    ls ${REPO_DIR} -R
    echo "::endgroup::"
    echo "-------------------"

    echo "::group::Listing contents of current directory recursively"
    ls -R
    echo "::endgroup::"
    echo "-------------------"

    echo "::group::Listing contents of parent directory recursively"
    ls .. -R
    echo "::endgroup::"
    echo "-------------------"
fi

echo "::group::Creating dox Files from Example Header Lines"
curl -SL ${WORKFLOW_DIR}documentExamples.py -o documentExamples.py
python -u documentExamples.py
echo "::endgroup::"

# only continue if these steps fail
# doing this here to print the Doxygen log if it fails
set +e

echo -e "\e[36mGenerating Doxygen code documentation...\e[0m"
echo "::group::Doxygen Run Log"
# Redirect both stderr and stdout to the log file AND the console.
# case sensitive!
if [ -e Doxyfile ]; then
    doxygen Doxyfile 2>&1 | tee output_doxygen_run.log
else
    doxygen doxyfile 2>&1 | tee output_doxygen_run.log
fi

result_code_doxygen=${PIPESTATUS[0]}
echo "::endgroup::"
echo "::group::Doxygen Output"
echo "$(<output_doxygen.log)"
echo "::endgroup::"
if [[ "$result_code_doxygen" -ne "0" ]]; then
    echo -e "::Error::Doxygen encountered an error while running!"
    echo -e "\e[31mFinished running doxygen with result code: $result_code_doxygen\e[0m"
else
    echo -e "\e[32mDoxygen completed successfully.\e[0m"
fi

# if [[ "$result_code_doxygen" -ne "0" ]]; then exit $result_code_doxygen; fi

# go back to immediate exit
set -e

if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "::group::Listing current directory contents"
    echo "Current directory: $PWD"
    ls
    echo "::endgroup::"

    echo "-------------------"

    echo "::group::Listing contents of $GITHUB_WORKSPACE/code_docs/"
    ls $GITHUB_WORKSPACE/code_docs/
    echo "::endgroup::"

    echo "-------------------"

    echo "::group::Listing contents of ${REPO_DIR} recursively"
    ls ${REPO_DIR} -R
    echo "::endgroup::"

    echo "-------------------"

    echo "::group::Listing contents of ${REPO_DIR}_Doxygen recursively"
    ls ${REPO_DIR}_Doxygen -R
    echo "::endgroup::"
    echo "-------------------"
fi

# Fix up xml sections before running m.css
echo "::group::Fixing XML sections"
curl -SL ${WORKFLOW_DIR}fixSectionsInXml.py -o fixSectionsInXml.py
python -u fixSectionsInXml.py 2>&1
echo "::endgroup::"

# echo -e "\e[36mFixing copied function documentation in group documentation\e[0m"
# python -u fixFunctionsInGroups.py

# only continue if these steps fail
# doing this here to print the m.css log if it fails
set +e

# Run m.css
echo -e "\e[36mRunning m.css Doxygen post-processor...\e[0m"
echo "::group::m.css Run Log"
if [ "$RUNNER_DEBUG" = "1" ]; then
    python -u "${MCSS_DIR}documentation/doxygen.py" "mcss-conf.py" --no-doxygen --output "${REPO_DIR}/docs/output_mcss.log" --templates "${MCSS_DIR}documentation/templates/EnviroDIY" --debug | tee output_mcss_run.log
    result_code_mcss=${PIPESTATUS[0]}
else
    python -u "${MCSS_DIR}documentation/doxygen.py" "mcss-conf.py" --no-doxygen --output "${REPO_DIR}/docs/output_mcss.log" --templates "${MCSS_DIR}documentation/templates/EnviroDIY" | tee output_mcss_run.log
    result_code_mcss=${PIPESTATUS[0]}
fi

echo "::endgroup::"
echo "::group::m.css Output"
echo "$(<output_mcss.log)"
echo "::endgroup::"
if [[ "$result_code_mcss" -ne "0" ]]; then
    echo -e "::Error::m.css encountered an error while running!"
    echo -e "\e[31mFinished running m.css with result code: $result_code_mcss\e[0m"
else
    echo -e "\e[32mm.css completed successfully.\e[0m"
fi

# if [[ "$result_code_mcss" -ne "0" ]]; then exit $result_code_mcss; fi

if [ "$result_code_doxygen" -ne "0" ] || [ "$result_code_mcss" -ne "0" ]; then
    # Echo outputs to output and step summaries
    echo "doxygen_warnings=$(cat output_doxygen.log)" >>$GITHUB_OUTPUT
    echo "mcss_warnings=$(cat output_mcss.log)" >>$GITHUB_OUTPUT
    echo " ## Doxygen completed with the following warnings:" >>$GITHUB_STEP_SUMMARY
    echo "$(cat output_doxygen.log)" >>$GITHUB_STEP_SUMMARY
    echo "" >>$GITHUB_STEP_SUMMARY
    echo "## mcss Doxygen post-processing completed with the following warnings:" >>$GITHUB_STEP_SUMMARY
    echo "$(cat output_mcss.log)" >>$GITHUB_STEP_SUMMARY
    exit $((result_code_doxygen + result_code_mcss))
fi

# go back to immediate exit
set -e

# copy functions so they look right
echo "::group::Copying function docs"
curl -SL ${WORKFLOW_DIR}copyFunctions.py -o copyFunctions.py
python -u copyFunctions.py 2>&1
echo "::endgroup::"

# delete stupid links
echo "::group::Removing stupid sub-page links"
curl -SL ${WORKFLOW_DIR}removeStupidLinks.py -o removeStupidLinks.py
python -u removeStupidLinks.py 2>&1
echo "::endgroup::"

# # Generate Arduino keywords using doxygen2keywords.xsl and Saxon
# echo -e "\e[36mConverting the Doxygen output to an Arudino keywords file\e[0m"
# java  -jar "C:\Users\sdamiano\Downloads\SaxonHE12-4J\saxon-he-12.4.jar" -o:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensors\keywords.txt" -s:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensorsDoxygen\xml\index.xml" -xsl:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\workflows\docs\doxygen2keywords.xsl"
# perl -i -ne 'print if ! $x{$_}++' "C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensors\keywords.txt"


echo "::notice::Finished generating documentation"
