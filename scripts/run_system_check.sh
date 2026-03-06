#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python backend/system_tests/full_system_check.py
