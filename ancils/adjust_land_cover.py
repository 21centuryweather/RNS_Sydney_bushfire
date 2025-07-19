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

# open land cover
# cb = ants.load_cube(f'{ancil_path}/qrparm.veg.frac_cci')
cb = ants.load_cube(f'{ancil_path}/qrparm.veg.frac.urb2t')

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

# Get the pseudo_level coordinate
pseudo_levels = cb.coord('pseudo_level').points

pseudo_map = {  'broad_leaf': 1,
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

# Find indices for specific land cover types
soil_idx = np.where(pseudo_levels == pseudo_map['soil'])[0][0]
shrub_idx = np.where(pseudo_levels == pseudo_map['shrub'])[0][0]

# Apply adjustments within the masked area
# First, zero out all fractions within the mask
cb_adjusted.data[:, mask] = 0.0

# Set the desired fractions
cb_adjusted.data[soil_idx, mask] = 0.80  # soil
cb_adjusted.data[shrub_idx, mask] = 0.20  # shrub

# # Ensure fractions still sum to 1 (optional normalization)
total = np.sum(cb_adjusted.data, axis=0)
assert total.all() == 1.0, "Fractions do not sum to 1 after adjustment."

# # testing
# import xarray as xr
# import matplotlib.pyplot as plt
# # plot all dim_0 levels using xarray
# ds = xr.DataArray().from_iris(cb_adjusted)
# ds.plot(col='dim_0', col_wrap=5, cmap='viridis', vmin=0, vmax=1)
# # give titles based on pseudo_map levels
# for i, level in enumerate(pseudo_levels):
#     plt.gcf().axes[i].set_title(f"{level} - {list(pseudo_map.keys())[list(pseudo_map.values()).index(level)]}")
