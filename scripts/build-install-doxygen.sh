#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

# NOTE: Install these dependencies for building Doxygen using awalsh128/cache-apt-pkgs-action@v1
#   - name: Install or Restore apt-get packages for building Doxygen
#     id: install_doxygen_build_deps
#     if: ${{ inputs.build_doxygen && steps.check_doxygen_version.outputs.correct_doxygen != 'true'}}
#     uses: awalsh128/cache-apt-pkgs-action@v1
#     with:
#       packages: >
#         build-essential flex bison
#       version: ${{ inputs.rebuild_cache_number }}
#       debug: false

# install all the dependencies for make for Doxygen
# sudo apt-get update
# sudo apt-get -y install build-essential
# sudo apt-get -y install flex
# sudo apt-get -y install bison

cd $GITHUB_WORKSPACE

# Remove any old versions
sudo apt-get remove doxygen

# Build instructions from: https://www.stack.nl/~dimitri/doxygen/download.html
echo "\e[32mCloning doxygen repository...\e[0m"
git clone https://github.com/doxygen/doxygen.git doxygen-src --branch $DOXYGEN_VERSION --depth 1

cd doxygen-src

echo "\e[32mCreate build folder...\e[0m"
mkdir build
cd build

echo "\e[32mMake...\e[0m"
sudo cmake -G "Unix Makefiles" ..
sudo make
sudo make install

echo "\e[32mDone building doxygen.\e[0m"
echo "\e[32mdoxygen is now installed at : \e[0m" $(type -a doxygen)

echo "\e[32m\n\n\nCurrent Doxygen version...\e[0m"
doxygen -v
echo "\n\n\n"
