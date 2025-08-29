#!/bin/bash
#PBS -q normal
#PBS -l ncpus=4
#PBS -l mem=16GB
#PBS -l walltime=01:00:00
#PBS -l storage=gdata/hh5+gdata/access+gdata/fy29+scratch/fy29
#PBS -l wd
#PBS -l jobfs=10GB
#PBS -P fy29

set -e

module use /g/data3/hh5/public/modules
module load conda/analysis3

echo "Starting ancillary file adjustments for Blue Mountains bushfire simulation..."

# Define base paths
ANCIL_BASE="/scratch/$PROJECT/$USER/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198"

# Define file paths
LAND_COVER_FILE="${ANCIL_BASE}/qrparm.veg.frac.urb2t"
ALBEDO_FILE="${ANCIL_BASE}/qrparm.soil_cci"
FIRE_MASK_FILE="${ANCIL_BASE}/fire_mask.nc"

# Check if fire mask exists
if [ ! -f "${FIRE_MASK_FILE}" ]; then
    echo "ERROR: Fire mask file not found: ${FIRE_MASK_FILE}"
    echo "Please run create_fire_mask.py first to generate the mask file"
    echo "Example: python create_fire_mask.py --output_dir /scratch/public/as9583/"
    exit 1
fi

echo "Using fire mask: ${FIRE_MASK_FILE}"

echo "==================================================================="
echo "1. Adjusting land cover fractions"
echo "==================================================================="
python adjust_land_cover.py \
    --fpath "${LAND_COVER_FILE}" \
    --mask_file "${FIRE_MASK_FILE}" \
    --plot

if [ $? -eq 0 ]; then
    echo "Land cover adjustment completed successfully"
fi

echo ""
echo "=============================================="
echo "2. Adjusting soil albedo"
echo "=============================================="
python adjust_albedo.py \
    --fpath "${ALBEDO_FILE}" \
    --mask_file "${FIRE_MASK_FILE}" \
    --plot

if [ $? -eq 0 ]; then
    echo "Albedo adjustment completed successfully"
fi

echo ""
echo "==================================================================="
echo "Ancillary file adjustments completed successfully!"
echo "Used fire mask: ${FIRE_MASK_FILE}"
echo "Adjusted files:"
echo "  - Land cover: ${LAND_COVER_FILE}_updated"
echo "  - Albedo: ${ALBEDO_FILE}_updated"
echo "Plots saved in: ${ANCIL_BASE}/"
echo ""
echo "Note: To adjust soil moisture in initial conditions, run:"
echo "  qsub run_adjust_soil_moisture.sh"
echo "==================================================================="

