#!/bin/bash

set -e

# Save current dir, go up one level to project root
pushd "$(dirname "$0")/.." > /dev/null

cp output/semantic_analysis/* examples/
cp output/bias_analysis/* examples/
cp output/owl_influence-mini/influence-mini_full.owl examples/
cp output/owl_dima/dima_full.owl examples/

# Return to original directory
popd > /dev/null
