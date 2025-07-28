# RNS_Sydney_bushfire
Impact of megafires on weather

## Contributions
- Abby Smyth: experiment design, final model runs, all analysis
- Ailie Gallant: experiment design, supervision
- Mathew Lipson: ancil adjustment code, develop u-dr216 suite for 8 experiments, initial model runs

## Configuration

Model: ACCESS-rAM (with OSTIA varying sea surface temperature)  
Model suite: https://code.metoffice.gov.uk/trac/roses-u/browser/d/r/2/1/6/trunk  
Period: 20200114T0000Z to 20200212T0000Z (30 days)  

Domain:
- Outer: GAL9 at 0.11° (~12.2 km) (BARRA-R2 initialised)
- Inner: RAL3p2 at 0.198° (~2.2km at equator)

Experiments:
8 sets (see below)

![Domains](./ancils/Bluemountains_domains_surface_altitude.png)

## Compute

Major tasks for single experiment:

|               | y_npts | x_npts | nproc | CPUS | SU/12hrs | walltime/12hrs  |
|---------------|--------|--------|-------|------|----------|-----------------|
| ec_um_recon   |        |        |       | 192  | 96       | 1 min           |
| d11000 fcst   | 300    | 300    | 16x12 | 192  | 19       | 3 min           |
| d11000 recon  |        |        |       | 192  | 5        | 1 min           |
| d0198  fcst   | 450    | 450    | 24x24 | 576  | 230      | 12 min          |
| d0198  recon  |        |        |       | 192  | 8        | 1 min           |

### Total per day per experiment

- ~725 SU per day
- ~30 min walltime per day

## Experiments

Description of experiments:

<img width="468" height="166" alt="image" src="https://github.com/user-attachments/assets/70c69e67-933a-4bd1-ba6c-e3146e6b6e76" />

The simulation suite `u-dg216` has been updated so that any simulations (e.g. regions, resolutions, models) with "drysoil" in their name will have their soil initial conditions reduced by [u-dr216/bin/adjust_soil_ics.py](https://code.metoffice.gov.uk/trac/roses-u/browser/d/r/2/1/6/trunk/bin/adjust_soil_ics.py). 

Any simulation with "albedo" in their name will be pointed to a pre-adjusted ancil by the optional file [u-dr216/app/um/opt/rose-app-burnt_albedo.conf](https://code.metoffice.gov.uk/trac/roses-u/browser/d/r/2/1/6/trunk/app/um/opt/rose-app-burnt_albedo.conf). Any simulation with "bare" in the name will be pointed to [u-dr216/app/um/opt/rose-app-burnt_bare.conf](https://code.metoffice.gov.uk/trac/roses-u/browser/d/r/2/1/6/trunk/app/um/opt/rose-app-burnt_bare.conf). These are pre-adjusted by python scripts in the ancils folder (see below for instructions). Simulations with both bare and albedo in their name will have both aspects updated.

# To run on Gadi:

## Generate ancils

1. Clone this repository: `git clone git@github.com:21centuryweather/RNS_Sydney_bushfire.git`
1. Get ancil suite: `rosie checkout u-dg767`
2. Copy this [experiment ancils opt file](./ancils/rose-suite-rns_bluemountains.conf) to your `~/roses/u-dg767/opt`
3. From u-dg767 folder, run suite with opt file: `rose suite-run -O rns_bluemountains --name=ancil_blue_mountains`
4. When complete, create a netcdf of the fire mask with [ancils/create_fire_mask.py](./ancils/create_fire_mask.py) (update script as necessary)
5. Update [albedo](./ancils/adjust_albedo.py) and [land cover](./ancils/adjust_land_cover.py) by running [ancils/run_adjust_ancils.sh](./ancils/run_adjust_ancils.sh) (update PBS details for your projects as necessary). Use `qsub run_adjust_ancils.sh` to submit to the PBS queue.

## Run simulations

1. Get simulation suite u-dr216: `rosie checkout u-dr216`
2. Go to suite folder: `cd ~/roses/u-dr216`
3. Run suite: `rose suite-run`

## Process outputs
1. Update [preprocessing/convert_um_to_netcdf.py](./preprocessing/convert_um_to_netcdf.py) for your project and user, and select which variables to save to netcdf
2. Run directly in python, or use the PBS script [preprocessing/run_convert_um_to_netcdf.py](./preprocessing/run_convert_um_to_netcdf.py) after updating PBS flags for your project
3. Netcdf outputs are in: /g/data/{project}/{user}/cylc-run/u-dr216/netcdf
