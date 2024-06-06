#!/bin/bash

# Script modified from scripts by Jeroen de Bruijn, thephez, and Adafruit
# https://gist.github.com/vidavidorra/548ffbcdae99d752da02
# https://github.com/thephez/doxygen-travis-build
# https://learn.adafruit.com/the-well-automated-arduino-library/travis-ci

# Set options,
set -e # Exit with nonzero exit code if anything fails
set -v # Prints shell input lines as they are read.
set -x # Print command traces before executing command.

# Update the style sheets
echo "::group::Updating style sheets"
cd $GITHUB_WORKSPACE/code_docs/m.css
echo "\n\e[32mUpdate the style sheets\e[0m"
cd $GITHUB_WORKSPACE/code_docs/m.css/css/EnviroDIY
python -u $GITHUB_WORKSPACE/code_docs/m.css/css/postprocess.py "m-EnviroDIY.css"
python -u $GITHUB_WORKSPACE/code_docs/m.css/css/postprocess.py "m-EnviroDIY.css" "m-documentation.css" -o "m-EnviroDIY+documentation.compiled.css"
python -u $GITHUB_WORKSPACE/code_docs/m.css/css/postprocess.py "m-EnviroDIY.css" "m-theme-EnviroDIY.css" "m-documentation.css" --no-import -o "m-EnviroDIY.documentation.compiled.css"
cp $GITHUB_WORKSPACE/code_docs/m.css/css/EnviroDIY/m-EnviroDIY+documentation.compiled.css $GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/}/docs/css
echo "::endgroup::"

cd $GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/}/docs
# download the markdown pre-filter
curl https://raw.githubusercontent.com/EnviroDIY/workflows/main/docs/markdown_prefilter.py -o markdown_prefilter.py

echo "\n\e[32mCurrent Doxygen version...\e[0m"
$GITHUB_WORKSPACE/doxygen-src/build/bin/doxygen -v 2>&1

echo "::group::Listing directory contents"
echo "$PWD"
ls $GITHUB_WORKSPACE/code_docs/
ls $GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/} -R
echo "::endgroup::"

# echo "\n\e[32mCreating dox files from example read-me files\e[0m"
# curl https://raw.githubusercontent.com/EnviroDIY/workflows/main/docs/documentExamples.py -o documentExamples.py
# python -u documentExamples.py

# only continue if these steps fail
# doing this here to print the Doxygen log if it fails
set +e

echo "\n\e[32mGenerating Doxygen code documentation...\e[0m"
echo "::group::Doxygen Run Log"
# Redirect both stderr and stdout to the log file AND the console.
$GITHUB_WORKSPACE/doxygen-src/build/bin/doxygen Doxyfile 2>&1 | tee output.log
result_code=$(PIPESTATUS[0])
echo "::endgroup::"
echo "::group::Doxygen Output"
echo "$(<output_doxygen.log )"
echo "::endgroup::"
if [ "$result_code" -ne "0" ] ; then exit $result_code; fi

# go back to immediate exit
set -e

echo "\n\e[32mFixing errant xml section names in examples as generated by Doxygen...\e[0m"
curl https://raw.githubusercontent.com/EnviroDIY/workflows/main/docs/fixSectionsInXml.py -o fixSectionsInXml.py
python -u fixSectionsInXml.py 2>&1

# echo "\n\e[32mFixing copied function documentation in group documentation\e[0m"
# python -u fixFunctionsInGroups.py

echo "\n\e[32Running m.css Doxygen post-processor...\e[0m"
echo "::group::m.css Run Log"
python -u $GITHUB_WORKSPACE/code_docs/m.css/documentation/doxygen.py "mcss-conf.py" --no-doxygen --output "$GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/}/docs/output_mcss.log" --templates "$GITHUB_WORKSPACE/code_docs/m.css/documentation/templates/EnviroDIY"
echo "::endgroup::"
echo "::group::m.css Output"
echo "$(<output_mcss.log )"
echo "::endgroup::"

# copy functions so they look right
echo "\n\e[32mCopying function documentation\e[0m"
curl https://raw.githubusercontent.com/EnviroDIY/workflows/main/docs/copyFunctions.py -o copyFunctions.py
python -u copyFunctions.py 2>&1

# # Generate Arduino keywords using doxygen2keywords.xsl and Saxon
# echo "\n\e[32mConverting the Doxygen output to an Arudino keywords file\e[0m"
# java  -jar "C:\Users\sdamiano\Downloads\SaxonHE12-4J\saxon-he-12.4.jar" -o:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensors\keywords.txt" -s:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensorsDoxygen\xml\index.xml" -xsl:"C:\Users\sdamiano\Documents\GitHub\EnviroDIY\workflows\docs\doxygen2keywords.xsl"
# perl -i -ne 'print if ! $x{$_}++' "C:\Users\sdamiano\Documents\GitHub\EnviroDIY\ModularSensors\keywords.txt"
