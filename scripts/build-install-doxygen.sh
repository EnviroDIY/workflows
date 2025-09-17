#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

cd $GITHUB_WORKSPACE

# Remove any old versions
sudo apt-get remove --purge "^doxygen.*"

# Build instructions from: https://www.stack.nl/~dimitri/doxygen/download.html
echo -e "\e[32mCloning doxygen repository...\e[0m"
git clone https://github.com/doxygen/doxygen.git doxygen-src --branch $DOXYGEN_TAG --depth 1

cd doxygen-src

echo -e "\e[32mCreate build folder...\e[0m"
mkdir build
cd build

echo -e "\e[32mMake...\e[0m"
sudo cmake -G "Unix Makefiles" ..
sudo make
sudo make install

echo -e "\e[32mDone building doxygen.\e[0m"
echo -e "\e[32mdoxygen is now installed at : \e[0m" $(type -a doxygen)

echo -e "\e[32m\n\n\nCurrent Doxygen version...\e[0m"
doxygen -v
echo -e "\n\n\n"
