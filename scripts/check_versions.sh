#!/bin/bash

#For testing
# DOXYGEN_VERSION=Release_1_11_0
# GRAPHVIZ_VERSION=11.0.0

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

# echo package versions: ${{ steps.install_apt_get_deps.outputs.package-version-list }}
# sudo apt update          # Fetches the list of available updates
# sudo apt upgrade -y      # Installs some updates; does not remove packages
# sudo apt full-upgrade -y # Installs updates; may also remove some packages, if needed
# sudo apt autoremove -y   # Removes any old packages that are no longer needed

doxygen -v
installed_doxygen=$(doxygen -v | cut -d ' ' -f1)
echo "$installed_doxygen"
echo "$installed_doxygen" | cut -d ' ' -f1
installed_doxygen=$(echo "$installed_doxygen" | cut -d ' ' -f1)
echo "Current Doxygen version is ${installed_doxygen}"
echo "Requested Doxygen version was ${DOXYGEN_VERSION}"
echo "installed_doxygen=${installed_doxygen}" >>$GITHUB_OUTPUT
if [ "$installed_doxygen" = "$DOXYGEN_VERSION" ]; then
    echo "::notice::The requested Doxygen version is already installed"
    echo "correct_doxygen=true" >>$GITHUB_OUTPUT
else
    echo "::warning::The installed Doxygen version is different than requestsed"
    echo "correct_doxygen=false" >>$GITHUB_OUTPUT
fi

installed_graphviz_full=$(dot -V 2>&1 | cut -d ' ' -f5)
echo "Full version of GraphViz ${installed_graphviz_full}"
installed_graphviz=$(echo "$installed_graphviz_full" | sed "s/dot - graphviz version //g")
installed_graphviz=$(echo "$installed_graphviz" | sed -r "s/ \(\d+\)//g")
echo "Substring of ${installed_graphviz}"
installed_graphviz="$(echo -e "${installed_graphviz}" | tr -d '[:space:]')"
echo "Current GraphViz version is ${installed_graphviz}"
echo "The requested GraphViz version was ${GRAPHVIZ_VERSION}"
if [ "$installed_graphviz" = "$GRAPHVIZ_VERSION" ]; then
    echo "::notice::The requested GraphViz version is already installed"
    echo "correct_graphviz=true" >>$GITHUB_OUTPUT
else
    echo "::warning::The installed GraphViz version is different than requestsed"
    echo "correct_graphviz=false" >>$GITHUB_OUTPUT
fi
