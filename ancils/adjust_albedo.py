'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import argparse

parser = argparse.ArgumentParser(description='adjusts soil albedo within a polygon to reduce albedo by a specified percentage')
parser.add_argument('--fpath', help='fpath to albedo file',default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/qrparm.soil_cci')
parser.add_argument('--polygon', help='path to polygon gpkg file to use for masking, if not provided will use example polygon', default=None)
parser.add_argument('--update', help='whether to create updated file and replace original with symlink', default=False, action='store_true')
parser.add_argument('--plot', help='whether to plot result', default=False, action='store_true')
args = parser.parse_args()

import ants
import geopandas as gpd
import numpy as np
import os
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import mule

###############################################################################

# Main inputs
polygon_fle = None

original_path = args.fpath

# temporary
args.plot = True
args.update = True

albedo_reduction_factor = 0.5  # 50% reduction

###############################################################################

def main(original_path):

    print(f'processing {original_path}')

    # Load albedo data
    cb = ants.load_cube(original_path, constraint='soil_albedo')

    # Create or load polygon
    if args.polygon is None:
        polygon = create_example_polygon()
    else:
        gdf = gpd.read_file(args.polygon)
        polygon = gdf.geometry.iloc[0]  # assuming single polygon

    if args.update:
        print('updating files')

        # make changes to albedo file with mule
        updated_fpath = original_path+'_updated'
        stashid = 220   # for soil albedo stash m01s00i220

        cb_adjusted = cb.copy()
        mask = create_mask_from_polygon(cb, polygon)
        
        # Reduce albedo by the specified factor within the polygon
        cb_adjusted.data[mask] *= (1 - albedo_reduction_factor)
        
        print(f"Original albedo range within mask: {cb.data[mask].min():.3f} to {cb.data[mask].max():.3f}")
        print(f"Adjusted albedo range: {cb_adjusted.data[mask].min():.3f} to {cb_adjusted.data[mask].max():.3f}")
        print(f"Number of grid cells modified: {np.sum(mask)}")

        save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot and args.update:
        print('plotting changes')
        # Get output directory for plots
        output_path = os.path.dirname(original_path)
        
        plot_albedo_comparison(cb, cb_adjusted, mask, albedo_reduction_factor, output_path)

def create_example_polygon(center_lon=150.49, center_lat=-33.5, size=1.0):
    """Create an example rectangular polygon."""
    half_size = size / 2
    polygon_coords = [
        (center_lon - half_size, center_lat - half_size),  # bottom-left
        (center_lon + half_size, center_lat - half_size),  # bottom-right
        (center_lon + half_size, center_lat + half_size),  # top-right
        (center_lon - half_size, center_lat + half_size),  # top-left
        (center_lon - half_size, center_lat - half_size)   # close the polygon
    ]
    polygon = Polygon(polygon_coords)
    print(f"Created example polygon centered at ({center_lon:.3f}, {center_lat:.3f})")
    return polygon

def create_mask_from_polygon(cb, polygon):
    """Create a boolean mask from polygon for the cube grid."""
    lons = cb.coord('longitude').points
    lats = cb.coord('latitude').points
    lon_2d, lat_2d = np.meshgrid(lons, lats)
    
    mask = np.zeros_like(lon_2d, dtype=bool)
    for i in range(lon_2d.shape[0]):
        for j in range(lon_2d.shape[1]):
            point = Point(lon_2d[i, j], lat_2d[i, j])
            mask[i, j] = polygon.contains(point)
    
    return mask

def save_adjusted_cube(cb_adjusted, output_path, original_path, stashid):
    """Save the adjusted cube using ANTS or MULE as fallback."""
    try:
        ants.save(cb_adjusted, output_path+'.nc')
        print(f"Adjusted albedo saved to {output_path} using ANTS.")
    except Exception as e:
        print(f"\nWARNING: Error saving adjusted cube with ANTS. Reason: {e}\n")
    
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
    im1 = ax1.imshow(cb.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.5)
    ax1.set_title('Original Albedo')
    plt.colorbar(im1, ax=ax1)

    # Adjusted albedo
    im2 = ax2.imshow(cb_adjusted.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.5)
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

