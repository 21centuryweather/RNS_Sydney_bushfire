'''
Create a fire mask NetCDF file from polygon data.
This script processes fire polygon data and creates a mask that can be reused
across multiple adjustment scripts (albedo, land cover, soil moisture).

Requires hh5, i.e.: 
    module use /g/data/hh5/public/modules;module load conda/analysis3
as xp65 does not have ants
'''

import argparse
import ants
import geopandas as gpd
import numpy as np
import os
import xarray as xr
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

parser = argparse.ArgumentParser(description='Create a fire mask NetCDF file from polygon data')
parser.add_argument('--fpath', help='Template file to get grid structure from', 
                    default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/qrparm.soil_cci')
                    # default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d11000/qrparm.soil_cci')
parser.add_argument('--polygon', help='Path to polygon gpkg file containing fire boundaries', 
                    default='/scratch/public/as9583/total_fires.gpkg')
parser.add_argument('--output', help='Output file for mask file', 
                    default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d0198/fire_mask.nc')
                    # default='/scratch/fy29/mjl561/cylc-run/ancil_blue_mountains/share/data/ancils/Bluemountains/d11000/fire_mask.nc')
parser.add_argument('--area_threshold', type=float, help='Minimum polygon area in square degrees', 
                    default=0.005)

args = parser.parse_args()

def main():
    print(f'Creating fire mask from: {args.polygon}')
    print(f'Using template file: {args.fpath}')
    
    # Load template file to get grid structure
    cb = ants.load_cube(args.fpath, constraint='soil_albedo')
    
    # Load polygon data
    gdf = gpd.read_file(args.polygon)
    print(f"Found {len(gdf)} polygons in the file")
    
    # Filter out very small polygons
    print(f"Filtering polygons smaller than {args.area_threshold} square degrees (~{args.area_threshold * 11100:.0f} km2)")
    gdf['area'] = gdf.geometry.area
    gdf_filtered = gdf[gdf['area'] >= args.area_threshold]
    
    print(f"After filtering: {len(gdf_filtered)} polygons remain")
    print(f"Removed {len(gdf) - len(gdf_filtered)} small polygons")
    
    # Create mask
    print("Creating mask from polygons...")
    mask = create_mask_from_polygons(cb, gdf_filtered)
    
    # Save mask as NetCDF
    save_mask_netcdf(mask, cb, args.output)
    
    print(f"\nMask creation complete!")
    print(f"Output file: {args.output}")
    print(f"Mask shape: {mask.shape}")
    print(f"Fire-affected grid cells: {np.sum(mask)} ({np.sum(mask)/mask.size*100:.2f}% of domain)")

def create_mask_from_polygons(cb, gdf):
    """Create a boolean mask from multiple polygons for the cube grid."""
    lons = cb.coord('longitude').points
    lats = cb.coord('latitude').points
    lon_2d, lat_2d = np.meshgrid(lons, lats)
    
    # Initialize combined mask
    combined_mask = np.zeros_like(lon_2d, dtype=bool)
    
    # Iterate through all polygons and combine masks
    for idx, polygon in enumerate(gdf.geometry):
        print(f"Processing polygon {idx+1}/{len(gdf)}")
        polygon_mask = np.zeros_like(lon_2d, dtype=bool)
        
        for i in range(lon_2d.shape[0]):
            for j in range(lon_2d.shape[1]):
                point = Point(lon_2d[i, j], lat_2d[i, j])
                polygon_mask[i, j] = polygon.contains(point)
        
        # Combine with overall mask using OR operation
        combined_mask = combined_mask | polygon_mask
        
        # Print progress
        cells_in_polygon = np.sum(polygon_mask)
        print(f"  Polygon {idx+1}: {cells_in_polygon} grid cells")
    
    total_cells = np.sum(combined_mask)
    print(f"Total grid cells in all polygons: {total_cells}")
    
    return combined_mask

def save_mask_netcdf(mask, cb, output_file):
    """Save the mask as a NetCDF file with proper coordinates and metadata."""
    
    # Get coordinates from the cube
    lons = cb.coord('longitude').points
    lats = cb.coord('latitude').points
    
    # Create xarray DataArray with metadata
    mask_da = xr.DataArray(
        mask.astype(int),  # Convert boolean to int (0/1)
        coords={'latitude': lats, 'longitude': lons},
        dims=['latitude', 'longitude'],
        name='fire_mask',
        attrs={
            'description': 'Fire scar mask (1=fire affected, 0=not affected)',
            'units': 'dimensionless',
            'created_by': 'create_fire_mask.py',
            'source_polygons': args.polygon,
            'area_threshold_sq_degrees': args.area_threshold,
            'total_fire_cells': int(np.sum(mask)),
            'grid_shape': f"{mask.shape[0]} x {mask.shape[1]}"
        }
    )
    
    # Save to NetCDF
    mask_da.to_netcdf(output_file)
    print(f'Saved fire mask as NetCDF: {output_file}')

if __name__ == '__main__':
    main()
