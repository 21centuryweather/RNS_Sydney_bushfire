'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''

import argparse

parser = argparse.ArgumentParser(description='adjusts initial condition soil moisture prior to recon to fix the "wet soil near cities" problem')
parser.add_argument('--fpath', help='fpath to startdump',default='/scratch/fy29/mjl561/cylc-run/u-dr216/share/cycle/20200114T0000Z/Bluemountains/d11000/GAL9/ics/GAL9_astart')
parser.add_argument('--polygon', help='path to polygon gpkg file to use for masking, if not provided will use example polygon', default=None)
parser.add_argument('--update', help='whether to create updated ics file and replace original with symlink', default=False, action='store_true')
parser.add_argument('--plot', help='whether to plot result to ics dir', default=False, action='store_true')
args = parser.parse_args()

import ants
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
import mule

###############################################################################

# Main inputs
polygon_fle = None
# ancil_path = '/scratch/fy29/mjl561/cylc-run/u-dr216/share/cycle/20200114T0000Z/Bluemountains/d11000/GAL9/ics'
# ancil_fname = 'GAL9_astart'

original_path = args.fpath

# temporary
args.plot = True
args.update = True


def main(original_path):

    print(f'processing {original_path}')

    # get soil moisture data
    cb = ants.load_cube(original_path, constraint='moisture_content_of_soil_layer')

    # Create or load polygon
    if args.polygon is None:
        polygon = create_example_polygon()
    else:
        gdf = gpd.read_file(args.polygon)
        polygon = gdf.geometry.iloc[0]  # assuming single polygon

    if args.update:
        print('updating files')

        # make changes to ics file with mule
        updated_fpath = original_path+'_updated'
        stashid = 9  # for moisture content of soil layer stash m01s00i009

        cb_adjusted = cb.copy()
        mask = create_mask_from_polygon(cb, polygon)
        # Broadcast mask to match the shape of cb_adjusted.data
        mask_broadcast = np.broadcast_to(mask, cb_adjusted.data.shape)
        cb_adjusted.data[mask_broadcast] *= 0.5  # reduce soil moisture by 50%

        save_adjusted_cube(cb_adjusted, updated_fpath, original_path, stashid)

    if args.plot and args.update:
        print('plotting changes')
        # Get bounds for plotting
        lons = cb.coord('longitude').points
        lats = cb.coord('latitude').points
        xmin, xmax = lons.min(), lons.max()
        ymin, ymax = lats.min(), lats.max()
        domain = 'GAL9'

        plot_domains(cb, cb_adjusted, xmin, xmax, ymin, ymax, domain)

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
        print(f"Adjusted soil moisture saved to {output_path} using ANTS.")
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
    print(f'saving updated ancil to {updated_fpath} with mule')
    try:
        ancil.to_file(updated_fpath)
    except Exception as e:
        print(e)
        print('WARNING: MULE validation being disabled')
        ancil.validate = lambda *args, **kwargs: True
        ancil.to_file(updated_fpath)

def plot_domains(cb,cb_updated,xmin,xmax,ymin,ymax,domain,cmap='RdYlBu'):

    import matplotlib.pyplot as plt
    import xarray as xr # for easier plotting
    import os

    plotpath = f'{os.path.dirname(args.fpath)}'

    # rename soil_model_level_number coord to depth where necessary
    if 'soil_model_level_number' in [coord.name() for coord in cb.coords()]:
        print('updating coord names to depth')
        cb.coord('soil_model_level_number').rename('depth')

    for i,depth in enumerate(cb.coord('depth')):
        depth = depth.points[0]

        print(f'plotting soil moisture')
        plt.close('all')
        ds = xr.DataArray().from_iris(cb).sel(depth=depth,latitude=slice(ymin,ymax),longitude=slice(xmin,xmax))
        vmax = float(ds.max())*0.95
        ds.plot(cmap=cmap,vmin=0,vmax=vmax)
        plt.savefig(f'{plotpath}/{domain}_sm_original_{i}.png', dpi=200)

        plt.close('all')
        ds = xr.DataArray().from_iris(cb_updated).sel(depth=depth,latitude=slice(ymin,ymax),longitude=slice(xmin,xmax))
        ds.plot(cmap=cmap,vmin=0,vmax=vmax)
        plt.savefig(f'{plotpath}/{domain}_sm_updated_{i}.png', dpi=200)

        break # just plot uppermost layer for now

    return


if __name__ == '__main__':
    print('functions loaded')

    main(args.fpath)