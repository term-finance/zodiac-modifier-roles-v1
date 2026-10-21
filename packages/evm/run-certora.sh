#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

usage="Usage: $0 <release>/<conf_file> <message>"
conf_file="${1?"${usage}"}"
conf_file="$(python3 "${script_dir}/certora/toolchain.py" "$conf_file" --field config)"
release="$(python3 "${script_dir}/certora/toolchain.py" "$conf_file" --field release)"
version="$(python3 "${script_dir}/certora/toolchain.py" "$conf_file")"
requirements="$(python3 "${script_dir}/certora/toolchain.py" "$conf_file" --field requirements)"
if ! installed_version="$(certoraRun --version)" || [[ "$installed_version" != "certora-cli ${version}" ]]; then
    printf 'This proof requires certora-cli %s. Install it in your active environment with:\n  pip install -r "%s"\n' "$version" "$requirements" >&2
    exit 1
fi
# A tagged release proves the guards at its tag.
python3 "${script_dir}/certora/pull_guards.py" "$release"

if [[ -f "${script_dir}/.env" ]]; then
    set -o allexport
    # shellcheck disable=SC1091
    source "${script_dir}/.env"
    set +o allexport
fi

export CERTORAKEY="${CERTORAKEY:?"CERTORAKEY is not set. Please set one in your .env file"}"
SOLC_VERSION="$(python3 "${script_dir}/certora/toolchain.py" "$conf_file" --field solc_version)"
export SOLC_VERSION
msg="${2:-"$(hostname) - ${conf_file} - $(date +%s)"}"

cd "$script_dir"
certoraRun "${conf_file}" --msg "${msg}" --wait_for_results all --rule_sanity basic
