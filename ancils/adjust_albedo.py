'''
Use: 
    module purge; module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''
import ants
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

ancil_path = '/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198'
polygon_fle = None
albedo_reduction_factor = 0.5

# open albedo
cbs = ants.load(f'{ancil_path}/qrparm.soil_cci')
cb = cbs.extract_cube('soil_albedo')

if polygon_fle is None:

    # Create an example rectangular polygon centred in the Blue Mountains
    center_lon, center_lat = 150.49, -33.5 
    polygon_coords = [
        (center_lon - 0.5, center_lat - 0.5),  # bottom-left
        (center_lon + 0.5, center_lat - 0.5),  # bottom-right
        (center_lon + 0.5, center_lat + 0.5),  # top-right
        (center_lon - 0.5, center_lat + 0.5),  # top-left
        (center_lon - 0.5, center_lat - 0.5)   # close the polygon
    ]
    
    polygon = Polygon(polygon_coords)
    print(f"Created example polygon centered at ({center_lon:.3f}, {center_lat:.3f})")
else:
    # Load the polygon from gpkg file
    gdf = gpd.read_file(polygon_file)
    polygon = gdf.geometry.iloc[0]  # assuming single polygon

# Create coordinate arrays for the land cover grid
lons = cb.coord('longitude').points
lats = cb.coord('latitude').points
lon_2d, lat_2d = np.meshgrid(lons, lats)

# Create mask for points inside polygon
mask = np.zeros_like(lon_2d, dtype=bool)
for i in range(lon_2d.shape[0]):
    for j in range(lon_2d.shape[1]):
        point = Point(lon_2d[i, j], lat_2d[i, j])
        mask[i, j] = polygon.contains(point)

# Adjust specific pseudo_levels within the polygon
# Example: Reduce broadleaf forest (pseudo_level 1) and increase grassland (pseudo_level 2)
cb_adjusted = cb.copy()

# Reduce albedo within the polygon
cb_adjusted.data[mask] *= 1 - albedo_reduction_factor

print(f"Original albedo range within mask: {cb.data[mask].min():.3f} to {cb.data[mask].max():.3f}")
print(f"Adjusted albedo range: {cb_adjusted.data[mask].min():.3f} to {cb_adjusted.data[mask].max():.3f}")
print(f"Number of grid cells modified: {np.sum(mask)}")

# Quick plot to visualize the change
import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))

# Original albedo
im1 = ax1.imshow(cb.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.5)
ax1.set_title('Original Albedo')
plt.colorbar(im1, ax=ax1)

# Adjusted albedo
im2 = ax2.imshow(cb_adjusted.data, origin='lower', cmap='Greys_r', vmin=0, vmax=0.5)
ax2.set_title(f'Adjusted Albedo (-{albedo_reduction_factor*100}% in polygon)')
plt.colorbar(im2, ax=ax2)

# Difference (should show the polygon area)
diff = cb_adjusted.data - cb.data
im3 = ax3.imshow(diff, origin='lower', cmap='Blues_r')
ax3.set_title('Difference (Adjusted - Original)')
plt.colorbar(im3, ax=ax3)

plt.tight_layout()
plt.show()

