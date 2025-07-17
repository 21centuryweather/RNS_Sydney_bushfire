This folder includes files necessary to create ancils

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
