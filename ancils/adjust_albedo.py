'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import argparse

parser = argparse.ArgumentParser(description='adjusts soil albedo within a polygon to reduce albedo by a specified percentage')
parser.add_argument('--fpath', help='fpath to albedo file',default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/qrparm.soil_cci')
parser.add_argument('--mask_file', help='path to fire mask NetCDF file', default='/scratch/public/as9583/fire_mask.nc')
parser.add_argument('--plot', help='whether to plot result', default=False, action='store_true')
args = parser.parse_args()

import ants
import numpy as np
import os
import matplotlib.pyplot as plt
import mule
import xarray as xr

###############################################################################

albedo_reduction_factor = 0.5  # 50% reduction

###############################################################################

def main(original_path):

    print(f'processing {original_path}')

    # Load albedo data
    cb = ants.load_cube(original_path, constraint='soil_albedo')

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

    # make changes to albedo file with mule
    updated_fpath = original_path+'_updated'
    stashid = 220   # for soil albedo stash m01s00i220

    cb_adjusted = cb.copy()
    
    # Reduce albedo by the specified factor within the polygon
    cb_adjusted.data[mask] *= (1 - albedo_reduction_factor)
    
    print(f"Original albedo range within mask: {cb.data[mask].min():.3f} to {cb.data[mask].max():.3f}")
    print(f"Adjusted albedo range: {cb_adjusted.data[mask].min():.3f} to {cb_adjusted.data[mask].max():.3f}")
    print(f"Number of grid cells modified: {np.sum(mask)}")

    save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot:
        print('plotting changes')
        # Get output directory for plots
        output_path = os.path.dirname(original_path)
        plot_albedo_comparison(cb, cb_adjusted, mask, albedo_reduction_factor, output_path)

    return

def save_adjusted_cube(cb_adjusted, output_path, original_path, stashid):
    """Save the adjusted cube using MULE"""
    
    # Convert iris cube to mule UMfile
    ancil = mule.AncilFile.from_file(original_path)
    arr = cb_adjusted.data.data
    
    for i, field in enumerate(ancil.fields):
        if field.lbuser4 == stashid:
            print(f'updating field {i}: {field.lbuser4}')
            array_provider = mule.ArrayDataProvider(arr)
            ancil.fields[i].set_data_provider(array_provider)
    
    # Save using mule
    print(f'saving updated ancil to {output_path} with mule')
    try:
        ancil.to_file(output_path)
    except Exception as e:
        print(e)
        print('WARNING: MULE validation being disabled')
        ancil.validate = lambda *args, **kwargs: True
        ancil.to_file(output_path)

def plot_albedo_comparison(cb, cb_adjusted, mask, reduction_factor, output_path):
    """Plot comparison of original vs adjusted albedo and save figure."""
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

    # Original albedo
    im1 = ax1.imshow(cb.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.3)
    ax1.set_title('Original Albedo')
    plt.colorbar(im1, ax=ax1)

    # Adjusted albedo
    im2 = ax2.imshow(cb_adjusted.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.3)
    ax2.set_title(f'Adjusted Albedo (-{reduction_factor*100}% in polygon)')
    plt.colorbar(im2, ax=ax2)

    # Difference (should show the polygon area)
    diff = cb_adjusted.data - cb.data
    im3 = ax3.imshow(diff, origin='lower', cmap='Blues_r')
    ax3.set_title('Difference (Adjusted - Original)')
    plt.colorbar(im3, ax=ax3)

    plt.tight_layout()
    
    # Save figure
    plt.savefig(f'{output_path}/adjusted_albedo.png', bbox_inches='tight')


if __name__ == '__main__':
    print('functions loaded')

    main(args.fpath)

