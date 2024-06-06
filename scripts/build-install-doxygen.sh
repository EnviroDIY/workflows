#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
set -v # Prints shell input lines as they are read.
set -x # Print command traces before executing command.

echo "\e[32m\n\n\nCurrent TeX version...\e[0m"
tex --version
echo "\n\n\n"

echo "\e[32m\n\n\nCurrent graphviz version...\e[0m"
dot -v
echo "\n\n\n"

cd $GITHUB_WORKSPACE

if [ ! -f $GITHUB_WORKSPACE/doxygen-src/build/bin/doxygen ]; then

    # Build instructions from: https://www.stack.nl/~dimitri/doxygen/download.html
    echo "\e[32mCloning doxygen repository...\e[0m"
    git clone https://github.com/doxygen/doxygen.git doxygen-src --branch $DOXYGEN_VERSION --depth 1

    cd doxygen-src

    echo "\e[32mCreate build folder...\e[0m"
    mkdir build
    cd build

    echo "\e[32mMake...\e[0m"
    cmake -G "Unix Makefiles" ..
    make
    sudo make install
    echo "\e[32mDone building doxygen.\e[0m"
    echo "\e[32mdoxygen path: \e[0m" $(pwd)
fi

echo "\e[32m\n\n\nCurrent Doxygen version...\e[0m"
doxygen -v
echo "\n\n\n"

cd $GITHUB_WORKSPACE/code_docs/${GITHUB_REPOSITORY#*/}
