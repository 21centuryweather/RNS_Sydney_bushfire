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

project = 'fy29'
user = 'mjl561'

########################

# define the suite and regions
cylc_id = 'u-dr216'
regions = ['control', 'drysoil']
regions = ['control']
save_to_netcdf = True # whether to save netcdf files

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

variables = ['stratiform_rainfall_amount','stratiform_rainfall_flux']
variables = ['land_sea_mask']
variables = ['stratiform_rainfall_amount']
variables = ['convective_rainfall_flux']
variables = ['surface_altitude']
variables = ['soil_moisture_l2']
variables = ['air_temperature']
variables = ['wind_speed_of_gust']
variables = ['stratiform_rainfall_flux']
variables = ['total_precipitation_rate']

# new variables
variables = ['geopotential_height_500hPa','geopotential_height_850hPa']
variables = ['upward_air_velocity_500hPa','upward_air_velocity_850hPa']
variables = ['wind_u_500hPa','wind_v_500hPa','wind_u_850hPa','wind_v_850hPa']

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
        da = xr.DataArray.from_iris(cb)
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
        
    # # Convert soil moisture from kg m-2 to volumetric water content (m3 m-3)
    # if variable.startswith('soil_moisture_l'):
    #     print('WARNING: converting soil moisture from kg m-2 to volumetric water content (m3 m-3)')
    #     layer_thickness = float(da.depth.values)  # m (soil layer thickness)
    #     water_density = 1000.0  # kg m-3
    #     da = da / (layer_thickness * water_density)
    #     da.attrs['units'] = 'm3 m-3'

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
        ds_all = xr.Dataset()
        
        # Get cycle list first
        cycle_list = sorted([x.split('/')[-2] for x in glob.glob(f'{cycle_path}/*/')])
        assert len(cycle_list) > 0, f"no cycles found in {cycle_path}"
        
        # Build complete experiment list for all regions
        exps = []
        exps_dirs = []
        for region in regions:
            first_cycle_path =  f'{cycle_path}/{cycle_list[0]}/{region}'

            # Dynamically discover experiment directories from first cycle
            # Include only second-level subdirectories (concatenated with parent using slash)
            for d in sorted(os.listdir(first_cycle_path)):
                d_path = os.path.join(first_cycle_path, d)
                if os.path.isdir(d_path):
                    # Second level subdirectories (concatenated with parent)
                    try:
                        for subdir in sorted(os.listdir(d_path)):
                            subdir_path = os.path.join(d_path, subdir)
                            if os.path.isdir(subdir_path):
                                exps.append(f"{region}_{d}_{subdir}")
                                exps_dirs.append(f"{region}/{d}/{subdir}")
                    except (PermissionError, OSError):
                        # Skip if we can't read the directory
                        pass
        
        print(f'Found experiment directories: {exps}')

        for exp, exp_dir in zip(exps, exps_dirs):

            # Extract region from experiment name
            region = exp.split('_')[0]

            da_list = []
            for i,cycle in enumerate(cycle_list):
                print('========================')
                print(f'getting {exp} {i}: {cycle}\n')

                # experiment path
                exp_base_path = f'{cycle_path}/{cycle}/{exp_dir}'
                
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

            if save_to_netcdf:
                fname = f'{datapath}/{opts["plot_fname"]}/{exp}_{opts["plot_fname"]}.nc'
                out_dir = os.path.dirname(fname)
                # make directory if it doesn't exist
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                print(f'saving to netcdf: {fname}')
                ds.to_netcdf(fname, unlimited_dims='time')

            # if 'd0198' in exp:
            #     print(f'adding {exp} to ds_all')
            #     ds_all[exp] = ds

            print(f'adding {exp} to ds_all')
            ds_all[exp] = ds

            del(ds, da, da_list)

    toc = time.perf_counter() - tic

    print(f"Timer {toc:0.4f} seconds")

    # # Plot comparison of all experiments
    # import matplotlib.pyplot as plt

    # # a plot that compares all items in ds_all with the control run

    # if 'ds_all' in locals() and len(ds_all.data_vars) > 0:
    #     print('ds_all is not empty, plotting comparison')

    #     # Get list of experiments
    #     exp_list = list(ds_all.data_vars)
    #     control_exp = 'control_d0198_RAL3P2'
        
    #     # Check if control experiment exists
    #     if control_exp not in exp_list:
    #         print(f"Warning: {control_exp} not found in ds_all. Available experiments: {exp_list}")
    #         control_exp = exp_list[0]  # Use first experiment as reference
            
    #     print(f"Using {control_exp} as control/reference")

    #     # Number of experiments
    #     n_exps = len(exp_list)
    #     ncols = min(3, n_exps)  # Max 3 columns
    #     nrows = int(np.ceil(n_exps / ncols))

    #     fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6 * ncols, 5 * nrows))
    #     if n_exps == 1:
    #         axes = [axes]  # Make it iterable for single subplot
    #     else:
    #         axes = axes.flatten()

    #     for i, exp_name in enumerate(exp_list):
    #         ax = axes[i]
            
    #         if exp_name == control_exp:
    #             # Plot control experiment
    #             if 'time' in ds_all[exp_name].dims:
    #                 ds_all[exp_name].mean(dim='time').plot(ax=ax, cmap=opts.get('cmap', 'viridis'))
    #             else:
    #                 ds_all[exp_name].plot(ax=ax, cmap=opts.get('cmap', 'viridis'))
    #             ax.set_title(f'{exp_name} (Control)')
    #         else:
    #             # Plot difference from control
    #             if 'time' in ds_all[exp_name].dims:
    #                 diff = (ds_all[exp_name]- ds_all[control_exp]).mean(dim='time')
    #             else:
    #                 diff = ds_all[exp_name] - ds_all[control_exp]
    #             diff.plot(ax=ax, cmap='RdBu_r', center=0, vmin=-2.5, vmax=2.5)
    #             ax.set_title(f'{exp_name} - {control_exp}')

    #     # Hide unused axes if any
    #     for j in range(n_exps, len(axes)):
    #         fig.delaxes(axes[j])

    #     plt.tight_layout()
    #     plt.show()


    # ds_all.mean(dim='time')
