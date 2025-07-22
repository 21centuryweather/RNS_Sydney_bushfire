'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import argparse

parser = argparse.ArgumentParser(description='adjusts land cover fractions within a polygon to set desired soil and shrub percentages')
parser.add_argument('--fpath', help='fpath to land cover file',default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/qrparm.veg.frac.urb2t')
parser.add_argument('--mask_file', help='path to fire mask NetCDF file', default='/scratch/public/as9583/fire_mask.nc')
parser.add_argument('--plot', help='whether to plot result', default=False, action='store_true')
args = parser.parse_args()

import os
import ants
import numpy as np
import xarray as xr
import mule

###############################################################################

soil_fraction=0.8                   # 80% soil in fire areas
shrub_fraction= 1. - soil_fraction 

###############################################################################

pseudo_map = {
    'broad_leaf': 1, 
    'needle_leaf': 2, 
    'c3_grass': 3, 
    'c4_grass': 4,
    'shrub': 5, 
    'urban': 6, 
    'lake': 7, 
    'soil': 8, 
    'ice': 9,
    'roof': 601, 
    'canyon': 602
}

###############################################################################

def main(original_path):

    print(f'processing {original_path}')

    # Load land cover data
    cb = ants.load_cube(original_path)

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

    # make changes to land cover file with mule
    updated_fpath = original_path+'_updated'
    stashid = 216  # for fraction of surface types stash m01s00i216

    cb_adjusted = cb.copy()
    cb_adjusted = adjust_land_cover(cb_adjusted, mask, soil_fraction, shrub_fraction)

    save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot:
        print('plotting changes')
        # Get output directory for plots
        output_path = os.path.dirname(original_path)
        
        plot_land_cover(cb_adjusted, output_path)

    return

def adjust_land_cover(cb_adjusted, mask, soil_fraction=0.8, shrub_fraction=0.2):
    """Adjust land cover fractions within the mask."""
    
    pseudo_levels = cb_adjusted.coord('pseudo_level').points
    
    # Find indices for specific land cover types
    soil_idx = np.where(pseudo_levels == pseudo_map['soil'])[0][0]
    shrub_idx = np.where(pseudo_levels == pseudo_map['shrub'])[0][0]
    
    # Apply adjustments within the masked area
    cb_adjusted.data[:, mask] = 0.0
    cb_adjusted.data[soil_idx, mask] = soil_fraction
    cb_adjusted.data[shrub_idx, mask] = shrub_fraction
    
    # Validate fractions sum to 1
    total = np.sum(cb_adjusted.data, axis=0)
    assert np.allclose(total, 1.0), "Fractions do not sum to 1 after adjustment."
    
    return cb_adjusted

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

def plot_land_cover(cb_adjusted, output_path):
    """Plot all land cover levels and save figure."""
    import xarray as xr
    import matplotlib.pyplot as plt

    pseudo_levels = cb_adjusted.coord('pseudo_level').points
    
    # Plot all dim_0 levels using xarray
    ds = xr.DataArray().from_iris(cb_adjusted)
    ds.plot(col='dim_0', col_wrap=5, cmap='turbo', vmin=0, vmax=1, figsize=(20, 8))
    
    # Give titles based on pseudo_map levels
    for i, level in enumerate(pseudo_levels):
        name = list(pseudo_map.keys())[list(pseudo_map.values()).index(level)]
        plt.gcf().axes[i].set_title(f"{level} - {name}")
    
    # Save figure
    plt.savefig(f'{output_path}/adjusted_land_cover.png', bbox_inches='tight')

if __name__ == '__main__':
    print('functions loaded')

    main(args.fpath)
