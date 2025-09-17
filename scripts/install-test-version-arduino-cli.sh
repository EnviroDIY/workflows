#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo -e "\e[32mCurrent Arduino CLI version:\e[0m"
arduino-cli version

echo -e "\e[32mDeleting any archived zips\e[0m"
rm -f home/arduino/downloads/${GITHUB_REPOSITORY#*/}.zip

echo -e "\e[32mDownloading library zip from ${LIBRARY_INSTALL_ZIP}\e[0m"
curl -L --retry 15 --retry-delay 0 ${LIBRARY_INSTALL_ZIP} --create-dirs -o home/arduino/downloads/${GITHUB_REPOSITORY#*/}.zip

echo -e "\e[32mUnzipping the library\e[0m"
unzip -o home/arduino/downloads/${GITHUB_REPOSITORY#*/}.zip -d home/arduino/downloads/ -x "*.git/*" "continuous_integration/*" "docs/*" "examples/*"

echo -e "\e[32mEnsuring no old directories exist\e[0m"
rm -r -f home/arduino/user/libraries/${GITHUB_REPOSITORY#*/}

echo -e "\e[32mCreating a new directory for the testing version of the library\e[0m"
mkdir -p home/arduino/user/libraries/${GITHUB_REPOSITORY#*/}

echo -e "\e[32mMoving the unzipped library to the new directory\e[0m"
if [ -z "${GITHUB_HEAD_REF}" ]; then
    echo -e "\n\e[36mExpected unzipped directory name (from commit SHA): home/arduino/downloads/${GITHUB_REPOSITORY#*/}-${GITHUB_SHA}\e[0m"
    mv home/arduino/downloads/${GITHUB_REPOSITORY#*/}-${GITHUB_SHA}/* home/arduino/user/libraries/${GITHUB_REPOSITORY#*/}
else
    INTERNAL_ZIP_NAME=$(echo "${GITHUB_HEAD_REF}" | sed -e 's/\//-/g')
    echo -e "\n\e[36mExpected unzipped directory name (from head of ${GITHUB_HEAD_REF}): home/arduino/downloads/${GITHUB_REPOSITORY#*/}-${SAVED_ZIP_NAME}\e[0m"
    mv home/arduino/downloads/${GITHUB_REPOSITORY#*/}-${INTERNAL_ZIP_NAME}/* home/arduino/user/libraries/${GITHUB_REPOSITORY#*/}
fi

echo -e "\e[32mUpdating the library index\e[0m"
arduino-cli --config-file continuous_integration/arduino_cli.yaml lib update-index

echo -e "\e[32mListing libraries detected by the Arduino CLI\e[0m"
arduino-cli --config-file continuous_integration/arduino_cli.yaml lib list

echo -e "\e[32mListing the contents of the Arduino library directory\e[0m"
ls home/arduino/user/libraries
