#!/bin/bash

#For testing
# DOXYGEN_VERSION=Release_1_11_0
# GRAPHVIZ_VERSION=11.0.0

# Set options,
set +e
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

installed_graphviz_full=$(dot -V 2>&1 | cut -d ' ' -f5)
result_code=${PIPESTATUS[0]}
if [ "$result_code" -ne "0" ] && [ "$status" -eq "0" ]; then
    echo "::notice::GraphViz is not installed!"
    exit 0;
fi

set -e
echo "Full version of GraphViz ${installed_graphviz_full}"
installed_graphviz=$(echo "$installed_graphviz_full" | sed "s/dot - graphviz version //g")
installed_graphviz=$(echo "$installed_graphviz" | sed -r "s/ \(\d+\)//g")
echo "Substring of ${installed_graphviz}"
installed_graphviz="$(echo "${installed_graphviz}" | tr -d '[:space:]')"
echo "Current GraphViz version is ${installed_graphviz}"
echo "The requested GraphViz version was ${GRAPHVIZ_VERSION}"
if [ "$installed_graphviz" = "$GRAPHVIZ_VERSION" ]; then
    echo "::notice::The requested GraphViz version (${installed_graphviz})is already installed"
    echo "correct_graphviz=true" >>$GITHUB_OUTPUT
else
    echo "::warning::The installed GraphViz version is different than requested"
    echo "correct_graphviz=false" >>$GITHUB_OUTPUT
fi
