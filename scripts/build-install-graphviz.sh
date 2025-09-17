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
sudo apt-get remove --purge "^libsodium.*"
sudo apt-get remove --purge "^graphviz.*"

# build and install libsodium (needed to build GraphViz)
curl -SL https://download.libsodium.org/libsodium/releases/LATEST.tar.gz -o LATEST.tar.gz
tar zxf LATEST.tar.gz
ls
cd libsodium-stable/
./configure
sudo make
sudo make install

# build and install graphviz
cd $GITHUB_WORKSPACE
curl -SL https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/$GRAPHVIZ_VERSION/graphviz-$GRAPHVIZ_VERSION.tar.gz -o graphviz-$GRAPHVIZ_VERSION.tar.gz
tar zxf graphviz-$GRAPHVIZ_VERSION.tar.gz
ls
cd graphviz-$GRAPHVIZ_VERSION/
./configure
sudo make
sudo make install

echo -e "\e[32mDone building GraphViz.\e[0m"
echo -e "\e[32mDot is now installed at : \e[0m" $(type -a dot)

echo -e "\e[32m\n\n\nCurrent GraphViz version...\e[0m"
dot -V

echo -e "\e[32m\n\n\nAttempting initial dot config...\e[0m"
sudo dot -c
echo -e "\n\n\n"
