# Ancils

This folder includes files necessary to create ancils

## Initial ancil creation

### rose-suite-rns_bluemountains.conf

This file is an optional ancil config file for u-dg767. 
To run it, after cloning the rAM3 u-dg767 suite, do:

```
cp rose-suite-rns_bluemountains.conf ~/roses/u-dg767/opt/
cd ~/roses/u-dg767
rose suite-run -O rns_bluemountains --name=ancil_blue_mountains
```

### plot_domains.py

This file plots domains found in defined cylc-run directory.
It requires xp65 modules, i.e. do:

`module use /g/data/xp65/public/modules;module load conda/analysis3`


`python plot_domains.py`

Output:

![domains](Bluemountains_domains_surface_altitude.png)

For different cylc-run dirs, or region names, update:

```
cylc_dir = 'ancil_blue_mountains'
region = 'Bluemountains'
```

## Adjusting ancils prior to suite-run

### create_fire_mask.py

Creates a fire mask NetCDF file from polygon gpkg data

Example usage:
`python create_fire_mask.py --fpath /path/to/template_file.nc --polygon /path/to/polygon.gpkg --output /path/to/output_mask.nc`

### adjust_albedo.py

Reduces soil albedo by a specified factor within fire-affected areas defined by a mask file.

Example usage:
`python adjust_albedo.py --fpath /path/to/albedo_file.nc --mask_file /path/to/fire_mask.nc --plot`

Must first run `create_fire_mask.py`

### adjust_land_cover.py

Adjusts land cover fractions in a UM ancillary file using a fire mask, setting soil and shrub percentages within fire-affected areas.

Example usage:
`python adjust_land_cover.py --fpath /path/to/land_cover_file.nc --mask_file /path/to/fire_mask.nc --plot`

Must first run `create_fire_mask.py`

## Adjusting initial conditions for soil moisture

Adjusts initial condition soil moisture prior to inner nest recon

This script will be incorporated into the suite and run automatically on the GAL9 domain

