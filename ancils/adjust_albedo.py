'''
Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import ants
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt

###############################################################################

# Main inputs
ancil_path = '/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198'
polygon_fle = None
albedo_fname = 'qrparm.soil_cci'
albedo_reduction_factor = 0.5

###############################################################################

def main():

    # Load albedo data
    cbs = ants.load(f'{ancil_path}/{albedo_fname}')
    cb = cbs.extract_cube('soil_albedo')

    # Create or load polygon
    if polygon_fle is None:
        polygon = create_example_polygon()
    else:
        gdf = gpd.read_file(polygon_fle)
        polygon = gdf.geometry.iloc[0]  # assuming single polygon

    # Create mask and adjust albedo
    mask = create_mask_from_polygon(cb, polygon)

    # Reduce albedo within the polygon
    cb_adjusted = cb.copy()
    cb_adjusted.data[mask] *= 1 - albedo_reduction_factor
    
    print(f"Original albedo range within mask: {cb.data[mask].min():.3f} to {cb.data[mask].max():.3f}")
    print(f"Adjusted albedo range: {cb_adjusted.data[mask].min():.3f} to {cb_adjusted.data[mask].max():.3f}")
    print(f"Number of grid cells modified: {np.sum(mask)}")

    # Save results
    adjusted_fpath = f'{ancil_path}/{albedo_fname}_adjusted'
    save_adjusted_cube(cb_adjusted, adjusted_fpath, f'{ancil_path}/{albedo_fname}')

    # Plot results
    plot_albedo_comparison(cb, cb_adjusted, mask, albedo_reduction_factor, ancil_path)

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

def save_adjusted_cube(cb_adjusted, output_path, original_path):
    """Save the adjusted cube using ANTS or MULE as fallback."""
    try:
        ants.save(cb_adjusted, output_path, saver='ancil')
        print(f"Adjusted albedo saved to {output_path} using ANTS.")
    except Exception as e:
        print(f"\nWARNING: Error saving adjusted cube with ANTS, using MULE instead. Reason: {e}\n")
        import mule
        
        # Convert iris cube to mule UMfile
        ancil = mule.AncilFile.from_file(original_path)
        arr = cb_adjusted.data.data
        
        for i, field in enumerate(ancil.fields):
            print(f'updating field {i}')
            array_provider = mule.ArrayDataProvider(arr)
            ancil.fields[i].set_data_provider(array_provider)
        
        # Save using mule
        print('\nWARNING: MULE validation being disabled\n')
        ancil.validate = lambda *args, **kwargs: True
        ancil.to_file(output_path)
        print(f"Adjusted albedo saved to {output_path} using MULE.")

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

if __name__ == "__main__":

    main()

