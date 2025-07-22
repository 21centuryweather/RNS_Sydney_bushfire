'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''

import argparse

parser = argparse.ArgumentParser(description='adjusts initial condition soil moisture prior to recon to fix the "wet soil near cities" problem')
parser.add_argument('--fpath', help='fpath to startdump',default='/scratch/fy29/mjl561/cylc-run/u-dr216/share/cycle/20200114T0000Z/Bluemountains/d11000/GAL9/ics/GAL9_astart')
parser.add_argument('--mask_file', help='path to fire mask NetCDF file', default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d11000/fire_mask.nc')
parser.add_argument('--plot', help='whether to plot result to ics dir', default=False, action='store_true')
args = parser.parse_args()

import ants
import numpy as np
import mule
import xarray as xr
import os

###############################################################################

sm_reduction_factor = 0.5  # 50% reduction

###############################################################################

def main(original_path):

    print(f'processing {original_path}')

    # get soil moisture data
    cb = ants.load_cube(original_path, constraint='moisture_content_of_soil_layer')

    # Load pre-created fire mask
    if os.path.exists(args.mask_file):
        print(f"Loading fire mask from: {args.mask_file}")
        mask_da = xr.open_dataarray(args.mask_file)
        mask = mask_da.values.astype(bool)
        print(f"Loaded mask with {np.sum(mask)} fire-affected grid cells")
    else:
        print(f"ERROR: Fire mask file not found: {args.mask_file}")
        print("Please run create_fire_mask.py first to generate the mask file")
        return

    print('updating files')

    # make changes to ics file with mule
    updated_fpath = original_path+'_updated'
    stashid = 9  # for moisture content of soil layer stash m01s00i009

    cb_adjusted = cb.copy()
    # Broadcast mask to match the shape of cb_adjusted.data
    mask_broadcast = np.broadcast_to(mask, cb_adjusted.data.shape)
    cb_adjusted.data[mask_broadcast] *= sm_reduction_factor

    save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot:
        print('plotting changes')
        # Get bounds for plotting (currently using the full domain)
        lons = cb.coord('longitude').points
        lats = cb.coord('latitude').points
        xmin, xmax = lons.min(), lons.max()
        ymin, ymax = lats.min(), lats.max()
        domain = 'GAL9'

        # Create comprehensive comparison plot
        plot_soil_moisture_comparison(cb, cb_adjusted, xmin, xmax, ymin, ymax, domain)

    return

def save_adjusted_cube(cb_adjusted, output_path, original_path, stashid):
    """Save the adjusted cube using MULE"""
    
    # Convert iris cube to mule UMfile
    ancil = mule.AncilFile.from_file(original_path)
    arr = cb_adjusted.data.data
    
    j = 0
    for i, field in enumerate(ancil.fields):
        if field.lbuser4 == stashid:
            print(f'updating field {i}: {field.lbuser4}')
            array_provider = mule.ArrayDataProvider(arr[j, :, :])
            ancil.fields[i].set_data_provider(array_provider)
            j += 1
    
    # Save using mule
    print(f'saving updated ancil to {output_path} with mule')
    try:
        ancil.to_file(output_path)
    except Exception as e:
        print(e)
        print('WARNING: MULE validation being disabled')
        ancil.validate = lambda *args, **kwargs: True
        ancil.to_file(output_path)

def plot_soil_moisture_comparison(cb, cb_adjusted, xmin, xmax, ymin, ymax, domain, cmap='RdYlBu'):
    """Plot comparison of original vs adjusted soil moisture for all 4 levels in a 3x4 grid."""

    import matplotlib.pyplot as plt
    
    plotpath = f'{os.path.dirname(args.fpath)}'
    
    # Convert to xarray for easier plotting
    ds_orig = xr.DataArray.from_iris(cb)
    ds_updated = xr.DataArray.from_iris(cb_adjusted)
    
    # Rename coordinate if needed
    if 'soil_model_level_number' in ds_orig.dims:
        ds_orig = ds_orig.rename({'soil_model_level_number': 'depth'})
        ds_updated = ds_updated.rename({'soil_model_level_number': 'depth'})
    
    # Subset to plotting domain
    ds_orig_subset = ds_orig.sel(latitude=slice(ymin, ymax), longitude=slice(xmin, xmax))
    ds_updated_subset = ds_updated.sel(latitude=slice(ymin, ymax), longitude=slice(xmin, xmax))
    
    # Calculate difference
    ds_diff = ds_updated_subset - ds_orig_subset
    
    # Create figure with 3 rows, 4 columns
    plt.close('all')
    fig, axes = plt.subplots(3, 4, figsize=(18, 12), sharey=True, sharex=True)
    
    for i in range(4):
        # Set color limits for this specific soil level
        vmax_orig = float(ds_orig_subset.isel(depth=i).max())
        vmin_orig = 0
        vmax_diff = max(abs(float(ds_diff.isel(depth=i).min())), 
                       abs(float(ds_diff.isel(depth=i).max())))
        
        # Row 1: Original soil moisture
        im1 = ds_orig_subset.isel(depth=i).plot(
            ax=axes[0, i], cmap=cmap, vmin=vmin_orig, vmax=vmax_orig,
        )
        axes[0, i].set_title(f'Original - Level {i+1}')
        axes[0, i].set_xlabel('Longitude' if i == 3 else '')
        axes[0, i].set_ylabel('Latitude' if i == 0 else '')
        
        # Row 2: Adjusted soil moisture  
        im2 = ds_updated_subset.isel(depth=i).plot(
            ax=axes[1, i], cmap=cmap, vmin=vmin_orig, vmax=vmax_orig,
        )
        axes[1, i].set_title(f'Adjusted - Level {i+1}')
        axes[1, i].set_xlabel('Longitude' if i == 3 else '')
        axes[1, i].set_ylabel('Latitude' if i == 0 else '')
        
        # Row 3: Difference
        im3 = ds_diff.isel(depth=i).plot(
            ax=axes[2, i], cmap='RdBu_r', vmin=-vmax_diff, vmax=vmax_diff,
        )
        axes[2, i].set_title(f'Difference - Level {i+1}')
        axes[2, i].set_xlabel('Longitude' if i == 3 else '')
        axes[2, i].set_ylabel('Latitude' if i == 0 else '')
    
    # Add main title
    fig.suptitle(f'{domain} Soil Moisture Comparison: Original, Adjusted, and Difference', 
                 fontsize=14, y=0.95)
    
    # Save figure
    plt.savefig(f'{plotpath}/{domain}_soil_moisture_comparison.png', 
                dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f'Saved soil moisture comparison plot: {plotpath}/{domain}_soil_moisture_comparison.png')

if __name__ == '__main__':
    print('functions loaded')

    main(args.fpath)