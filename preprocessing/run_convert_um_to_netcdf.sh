#!/bin/bash
#PBS -q normal
#PBS -l ncpus=12
#PBS -l mem=48GB
#PBS -l walltime=10:00:00
#PBS -l storage=gdata/xp65+gdata/fy29+scratch/ng72+gdata/ng72
#PBS -l wd
#PBS -l jobfs=10GB
#PBS -P ng72

set -eu
module purge
module use /g/data/xp65/public/modules
module load conda/analysis3
# module load dask-optimiser

python $HOME/Honours/github_honours/RNS_Sydney_bushfire/convert_um_to_netcdf.py
