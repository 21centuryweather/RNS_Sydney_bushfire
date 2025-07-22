__version__ = "2025-07-18"
__author__ = "Mathew Lipson"
__email__ = "m.lipson@unsw.edu.au"

'''
Create netcdf from um files

GADI ENVIRONMENT
----------------
module use /g/data/xp65/public/modules; module load conda/analysis3
'''

import time
import os
import xarray as xr
import iris
import numpy as np
import matplotlib.pyplot as plt
import glob
import sys
import warnings
import importlib
warnings.simplefilter(action='ignore', category=FutureWarning)

oshome=os.getenv('HOME')
sys.path.append(f'{oshome}/git/RNS_Sydney_bushfire')
import common_functions as cf
importlib.reload(cf)

# for timing
tic = time.perf_counter()

######## set up ########

cylc_id = 'u-dr216'
region = 'Bluemountains'
project = 'fy29'
user = 'mjl561'

########################

cycle_path = f'/scratch/{project}/{user}/cylc-run/{cylc_id}/share/cycle'
datapath = f'/g/data/{project}/{user}/cylc-run/{cylc_id}/netcdf'

variables_todo = [
    'land_sea_mask','air_temperature','surface_temperature','relative_humidity',
    'latent_heat_flux','sensible_heat_flux','air_pressure_at_sea_level',
    'surface_downwelling_shortwave_flux','surface_downwelling_longwave_flux',
    'dew_point_temperature', 'surface_net_downward_longwave_flux','wind_u','wind_v',
    'specific_humidity','specific_humidity_lowest_atmos_level','wind_speed_of_gust',
    'soil_moisture_l1','soil_moisture_l2','soil_moisture_l3','soil_moisture_l4',
    'soil_temperature_l1','soil_temperature_l2','soil_temperature_l3','soil_temperature_l4',
    'surface_runoff_flux','subsurface_runoff_flux','surface_total_moisture_flux',
    'surface_temperature','boundary_layer_thickness','surface_air_pressure',
    'fog_area_fraction','visibility','cloud_area_fraction',
    'stratiform_rainfall_amount','stratiform_rainfall_flux','convective_rainfall_amount', 'total_precipitation_rate',
    'toa_outgoing_shortwave_flux','toa_outgoing_shortwave_flux_corrected','toa_outgoing_longwave_flux',
    'surface_net_longwave_flux', 'surface_net_shortwave_flux','ground_heat_flux', 'surface_altitude'
    ]

variables_done = ['land_sea_mask','stratiform_rainfall_amount','stratiform_rainfall_flux',
             'air_temperature','wind_u','wind_v','wind_speed_of_gust','specific_humidity',
             'specific_humidity','soil_moisture_l1','surface_runoff_flux','surface_altitude']

variables = ['stratiform_rainfall_amount','stratiform_rainfall_flux']
variables = ['land_sea_mask']
variables = ['stratiform_rainfall_amount']
variables = ['total_precipitation_rate']
variables = ['convective_rainfall_flux']
variables = ['stratiform_rainfall_flux']
variables = ['surface_altitude']
variables = ['soil_moisture_l2']
variables = ['air_temperature']

###############################################################################

def get_um_data(exp, exp_path, opts):
    '''gets UM data, converts to xarray and local time'''

    print(f'processing {exp} (constraint: {opts["constraint"]})')

    fpath = f"{exp_path}/{opts['fname']}*"
    try:
        cb = iris.load_cube(fpath, constraint=opts['constraint'])
        # fix timestamp/bounds error in accumulations
        if cb.coord('time').bounds is not None:
            print('WARNING: updating time point to right bound')
            cb.coord('time').points = cb.coord('time').bounds[:,1]
        da = xr.DataArray().from_iris(cb)
    except Exception as e:
        print(f'trouble opening {fpath}')
        print(e)
        return None

    # fix time dimension name if needed
    if ('time' not in da.dims) and (variable not in ['land_sea_mask','surface_altitude']):
        print('WARNING: updating time dimension name from dim_0')
        da = da.swap_dims({'dim_0': 'time'})

    da = filter_odd_times(da)

    if opts['constraint'] in [
        'air_temperature', 
        'soil_temperature', 
        'dew_point_temperature', 
        'surface_temperature'
        ]:

        print('converting from K to °C')
        da = da - 273.15
        da.attrs['units'] = '°C'

    if opts['constraint'] in ['stratiform_rainfall_flux_mean']:
        print('converting from mm/s to mm/h')
        da = da * 3600.
        da.attrs['units'] = 'mm/h'

    if opts['constraint'] in ['moisture_content_of_soil_layer']:
        da = da.isel(depth=opts['level'])
        
    # Convert soil moisture from kg m-2 to volumetric water content (m3 m-3)
    if variable.startswith('soil_moisture_l'):
        print('WARNING: converting soil moisture from kg m-2 to volumetric water content (m3 m-3)')
        layer_thickness = float(da.depth.values)  # m (soil layer thickness)
        water_density = 1000.0  # kg m-3
        da = da / (layer_thickness * water_density)
        da.attrs['units'] = 'm3 m-3'

    return da

def filter_odd_times(da):

    if da.time.size == 1:
        return da

    minutes = da.time.dt.minute.values
    most_common_bins = np.bincount(minutes)
    most_common_minutes = np.flatnonzero(most_common_bins == np.max(most_common_bins))
    filtered = np.isin(da.time.dt.minute,most_common_minutes)
    filtered_da = da.sel(time=filtered)

    return filtered_da

if __name__ == "__main__":

    print('running variables:',variables)

    print('load dask')
    from dask.distributed import Client
    n_workers = int(os.environ['PBS_NCPUS'])
    local_directory = os.path.join(os.environ['PBS_JOBFS'], 'dask-worker-space')
    try:
        print(client)
    except Exception:
        client = Client(
            n_workers=n_workers,
            threads_per_worker=1, 
            local_directory = local_directory)

    ################## get model data ##################

    for variable in variables:
        print(f'processing {variable}')

        opts = cf.get_variable_opts(variable)

        cycle_list = sorted([x.split('/')[-2] for x in glob.glob(f'{cycle_path}/*/')])
        assert len(cycle_list) > 0, f"no cycles found in {cycle_path}"

        first_cycle_path =  f'{cycle_path}/{cycle_list[0]}/{region}'

        # Dynamically discover experiment directories from first cycle
        # Include only second-level subdirectories (concatenated with parent using slash)
        exp_dirs = []
        
        # First level directories
        for d in sorted(os.listdir(first_cycle_path)):
            d_path = os.path.join(first_cycle_path, d)
            if os.path.isdir(d_path):
                # Second level subdirectories (concatenated with parent)
                try:
                    for subdir in sorted(os.listdir(d_path)):
                        subdir_path = os.path.join(d_path, subdir)
                        if os.path.isdir(subdir_path):
                            exp_dirs.append(f"{d}_{subdir}")
                except (PermissionError, OSError):
                    # Skip if we can't read the directory
                    pass
        
        print(f'Found experiment directories: {exp_dirs}')

        for exp in exp_dirs:
            out_dir = f'{datapath}/{opts["plot_fname"]}'

            # make directory if it doesn't exist
            if not os.path.exists(f'{datapath}/{opts["plot_fname"]}'):
                os.makedirs(f'{datapath}/{opts["plot_fname"]}')

            da_list = []
            for i,cycle in enumerate(cycle_list):
                print('========================')
                print(f'getting {exp} {i}: {cycle}\n')

                # Dynamically find the experiment path by replacing only the first underscore with a slash
                exp_base_path = f'{cycle_path}/{cycle}/{region}/{exp.replace("_", "/", 1)}'
                
                # Find the um directory by searching through subdirectories
                exp_path = None
                if os.path.exists(exp_base_path):
                    # Walk through subdirectories to find the 'um' directory
                    for root, dirs, files in os.walk(exp_base_path):
                        if 'um' in dirs:
                            exp_path = os.path.join(root, 'um')
                            break
                
                # check if experiment path exists, if not skip this cycle
                if exp_path is None or not os.path.exists(exp_path):
                    print(f'path {exp_path} does not exist')
                    continue

                # check if any of the variables files are in the directory
                if len(glob.glob(f"{exp_path}/{opts['fname']}*")) == 0:
                    print(f'no files in {exp_path}')
                    continue

                da = get_um_data(exp, exp_path, opts)

                if da is None:
                    print(f'WARNING: no data found at {cycle}')
                else:
                    da_list.append(da)

                # for time invarient variables (land_sea_mask, surface_altitude) only get the first cycle
                if variable in ['land_sea_mask', 'surface_altitude']:
                    print('only needs one cycle')
                    break

            print('concatenating, adjusting, computing data')
            try: 
                ds = xr.concat(da_list, dim='time')
            except ValueError as e:
                print(f'ValueError: {e}')
                print('no data to concatenate, skipping')
                continue
            # da = da.compute()

            # set decimal precision to reduce filesize (definded fmt precision +1)
            precision = int(opts['fmt'].split('.')[1][0]) + 1
            if precision < 4:
                ds = ds.round(precision)
            else:
                print(f'WARNING: precision {precision} is too high, not rounding')

            # drop unessasary dimensions
            if 'forecast_period' in ds.coords:
                ds = ds.drop_vars('forecast_period')
            if 'forecast_reference_time' in ds.coords:
                ds = ds.drop_vars('forecast_reference_time')

            # chunk to optimise save
            if len(ds.dims)==3:
                itime, ilon, ilat = ds.shape
                ds = ds.chunk({'time':24,'longitude':ilon,'latitude':ilat})
            elif len(ds.dims)==2:
                ilon, ilat = ds.shape
                ds = ds.chunk({'longitude':ilon,'latitude':ilat})

            # encoding
            ds.time.encoding.update({'dtype':'int32'})
            ds.longitude.encoding.update({'dtype':'float32', '_FillValue': -999})
            ds.latitude.encoding.update({'dtype':'float32', '_FillValue': -999})
            ds.encoding.update({'zlib':'true', 'shuffle': True, 'dtype':opts['dtype'], '_FillValue': -999})

            fname = f'{datapath}/{opts["plot_fname"]}/{region}_{exp}_{opts["plot_fname"]}.nc'
            
            print(f'saving to netcdf: {fname}')
            ds.to_netcdf(fname, unlimited_dims='time')

    toc = time.perf_counter() - tic

    print(f"Timer {toc:0.4f} seconds")
