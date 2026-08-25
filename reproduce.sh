#!/usr/bin/env bash
# ==============================================================================
# MedicineApp — Academic Paper Benchmark Reproduction Suite
# Single command to reproduce all empirical findings reported in the paper.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "======================================================================"
echo " Starting MedicineApp Academic Benchmark Reproduction"
echo "======================================================================"

# 1. Activate Python virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# 2. Run master reproduction script
python scripts/reproduce_paper_experiments.py "$@"

echo "======================================================================"
echo " All Paper Experiments Successfully Reproduced!"
echo " Reports available at: reports/real_medication_roi_ablation"
echo "                       reports/real_layout_ablation"
echo "======================================================================"
