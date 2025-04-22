#!/usr/bin/env bash
#
# Builds a package containing both artifacts and source code.
#
# Example package structure:
#
#   my-package/
#     artifacts/
#       ... (output from yarn hardhat compile)
#     sources/
#       contracts/
#         ... (source code)
#       @openzeppelin/
#         ... (source code)
#       ... (other dependencies)
#
# Usage:
#
#   ./build-package.sh <output-dir>

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
usage="Usage: $0 <output-dir>"

set -o errexit
set -o nounset
set -o pipefail

# Ensure the output directory is provided using parameter expansion.
output_dir="${1:?Please provide an output directory. ${usage}}"
mkdir -p "${output_dir}"

# Copy the ${script_dir}/build/artifacts/ directory into the output directory.
cp -r "${script_dir}/build/artifacts" "${output_dir}"

# Flatten all .sol files in the contracts/ directory.
"${script_dir}/flatten-all.sh"

# Copy the ${script_dir}/flattened/ directory into the sources directory.
sources_dir="${output_dir}/sources"
mkdir -p "${sources_dir}"
cp -r "${script_dir}/flattened" "${sources_dir}"

# Copy dependencies into the sources directory.
mkdir -p "${sources_dir}/@openzeppelin"
cp -r "${script_dir}/node_modules/@openzeppelin/contracts-upgradeable" "${sources_dir}/@openzeppelin/contracts-upgradeable"
rm -rf "${sources_dir}/@openzeppelin/contracts-upgradeable/node_modules"
mkdir -p "${sources_dir}/@gnosis.pm/safe-contracts"
cp -r "${script_dir}/node_modules/@gnosis.pm/safe-contracts/contracts" "${sources_dir}/@gnosis.pm/safe-contracts/contracts"
rm -rf "${sources_dir}/@gnosis.pm/safe-contracts/contracts/node_modules"
mkdir -p "${sources_dir}/@gnosis.pm/zodiac"
cp -r "${script_dir}/node_modules/@gnosis.pm/zodiac/contracts" "${sources_dir}/@gnosis.pm/zodiac/contracts"
rm -rf "${sources_dir}/@gnosis.pm/zodiac/contracts/node_modules"
mkdir -p "${sources_dir}/@gnosis.pm/mock-contract"
cp -r "${script_dir}/node_modules/@gnosis.pm/mock-contract/contracts" "${sources_dir}/@gnosis.pm/mock-contract/contracts"
rm -rf "${sources_dir}/@gnosis.pm/mock-contract/contracts/node_modules"
