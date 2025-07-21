'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import argparse

parser = argparse.ArgumentParser(description='adjusts land cover fractions within a polygon to set desired soil and shrub percentages')
parser.add_argument('--fpath', help='fpath to land cover file',default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/qrparm.veg.frac.urb2t')
parser.add_argument('--polygon', help='path to polygon gpkg file to use for masking, if not provided will use example polygon', default=None)
parser.add_argument('--update', help='whether to create updated file and replace original with symlink', default=False, action='store_true')
parser.add_argument('--plot', help='whether to plot result', default=False, action='store_true')
args = parser.parse_args()

import os
import ants
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
import mule

###############################################################################

# Main inputs
polygon_fle = None

original_path = args.fpath

# temporary
args.plot = True
args.update = True

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

    # Create or load polygon
    if args.polygon is None:
        polygon = create_example_polygon()
    else:
        gdf = gpd.read_file(args.polygon)
        polygon = gdf.geometry.iloc[0]  # assuming single polygon

    if args.update:
        print('updating files')

        # make changes to land cover file with mule
        updated_fpath = original_path+'_updated'
        stashid = 216  # for fraction of surface types stash m01s00i216

        cb_adjusted = cb.copy()
        mask = create_mask_from_polygon(cb, polygon)
        cb_adjusted = adjust_land_cover(cb_adjusted, mask, soil_fraction=0.8, shrub_fraction=0.2)

        save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot and args.update:
        print('plotting changes')
        # Get output directory for plots
        output_path = os.path.dirname(original_path)
        
        plot_land_cover(cb_adjusted, output_path)

    return

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
    """Save the adjusted cube using ANTS or MULE as fallback."""
    try:
        ants.save(cb_adjusted, output_path+'.nc')
        print(f"Adjusted land cover saved to {output_path} using ANTS.")
    except Exception as e:
        print(f"\nWARNING: Error saving adjusted cube with ANTS. Reason: {e}\n")
    
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
