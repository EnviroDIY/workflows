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
