__version__ = "2025-07-17"
__author__ = "Mathew Lipson"
__email__ = "m.lipson@unsw.edu.au"

"""
To plot the ancillary domains
"""

import os
import sys
import iris
import xarray as xr
import rioxarray as rxr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import cartopy.crs as ccrs
import cartopy.geodesic as cgeo
import importlib

oshome=os.getenv('HOME')
gitpath=f'{oshome}/git/RNS_Sydney_1km'
sys.path.append(f'{gitpath}/plotting_code')
import common_functions as cf
importlib.reload(cf)

############## set up ##############

cylc_dir = 'ancil_blue_mountains'
region = 'Bluemountains'

####################################

ancil_path = f'{oshome}/cylc-run/{cylc_dir}/share/data/ancils/{region}'
plot_path = os.path.dirname(ancil_path) # parent dir of ancil_path
domains = os.listdir(ancil_path) # list of dirs in ancil_path

############## functions ##############

def plot_domain_orography():
    """
    Plot the orography of the different domains
    Mask out the ocean with the land sea mask ancil
    """

    data = {}
    for domain in domains:
        print(f'loading {domain} data')

        # get land sea mask ancil
        opts = get_variable_opts('land_sea_mask')
        fname = f'{ancil_path}/{domain}/{opts["fname"]}'
        cb = iris.load_cube(fname, constraint=opts["constraint"])
        lsm = xr.DataArray().from_iris(cb)

        # get orography ancil
        opts = get_variable_opts('surface_altitude')
        fname = f'{ancil_path}/{domain}/{opts["fname"]}'
        cb = iris.load_cube(fname, constraint=opts["constraint"])
        # convert to xarray and constrain to lsm
        data[domain] = xr.DataArray().from_iris(cb)
        # reindex lsm (rounding errors)
        lsm = lsm.reindex_like(data[domain],method='nearest')
        data[domain] = data[domain].where(lsm>0)

    # get resolutions of domains
    rslns = {dom: data[dom].rio.resolution() for dom in domains}
    # sort domains based on their size
    doms = sorted(domains, key=lambda x: data[x].shape[0]*rslns[x][0]*data[x].shape[1]*rslns[x][1], reverse=True)
    # doms = ['d0198']

    #############################################

    print(f"plotting")

    proj = ccrs.AlbersEqualArea()
    opts = get_variable_opts('surface_altitude')
    cmap = plt.get_cmap(opts['cmap'])
    # cmap = replace_cmap_min_with_white(cmap)

    plt.close('all')
    fig,ax = plt.subplots(nrows=1,ncols=1,figsize=(11,9),
                            sharey=True,sharex=True,
                            subplot_kw={'projection': proj},
                            )
    # update vmax based on outer domain, to nearest 100m
    vmax = np.floor(data[doms[0]].max().values/100)*100 - 100

    for domain in doms:
        print(f'plotting {domain}')
        im = data[domain].plot(ax=ax,cmap=cmap, vmin=opts['vmin'],vmax=vmax,
            add_colorbar=False, transform=proj)
        # draw rectangle around domain
        left, bottom, right, top = cf.get_bounds(data[domain])
        ax.plot([left, right, right, left, left], [bottom, bottom, top, top, bottom], 
            color='red', linewidth=1, linestyle='dashed' if domain=='SY_1' else 'solid')
        # label domain with white border around black text
        domain_text = f'{domain}: {data[domain].shape[0]}x{data[domain].shape[1]}'
        ax.text(right-0.1, top-0.1, f'{domain_text}', fontsize=8, ha='right', va='top', color='k',
                path_effects=[path_effects.withStroke(linewidth=1.5, foreground='w')])

    cbar_title = f"{opts['plot_title'].capitalize()} [{opts['units']}]"
    cbar = cf.custom_cbar(ax,im,cbar_loc='right')  
    cbar.ax.set_ylabel(cbar_title)
    cbar.ax.tick_params(labelsize=8)

    # # for cartopy
    ax.xaxis.set_visible(True)
    ax.yaxis.set_visible(True)
    ax.coastlines(color='k',linewidth=0.5,zorder=5)
    left, bottom, right, top = cf.get_bounds(data[doms[0]])
    ax.set_extent([left, right, bottom, top], crs=proj)
    
    ax = cf.distance_bar(ax,distance=200)
    ax.set_title(f'{region} domains')

    fname = f'{plot_path}/{region}_domains_{opts["plot_fname"]}.png'
    print(f'saving {fname}')
    fig.savefig(fname,dpi=300,bbox_inches='tight')

    return

def get_variable_opts(variable):
    '''standard variable options for plotting. to be updated within master script as needed'''

    # standard opts
    opts = {
        'constraint': variable,
        'plot_title': variable.replace('_',' '),
        'plot_fname': variable.replace(' ','_'),
        'units'     : '?',
        'obs_key'   : 'None',
        'obs_period': '1H',
        'fname'     : 'umnsaa_pvera',
        'vmin'      : None, 
        'vmax'      : None,
        'cmap'      : 'viridis',
        'threshold' : None,
        'fmt'       : '{:.2f}',
        }

    if variable == 'surface_altitude':
        opts.update({
        'constraint': 'surface_altitude',
        'units'     : 'm',
        'obs_key'   : 'None',
        'fname'     : 'qrparm.orog',
        'vmin'      : 0,
        'vmax'      : 1500,
        'cmap'      : 'terrain',
        })

    elif variable == 'land_sea_mask':
        opts.update({
            'constraint': 'm01s00i030',
            'plot_title': 'land sea mask',
            'plot_fname': 'land_sea_mask',
            'units'     : '1',
            'fname'     : 'qrparm.mask',
            'vmin'      : 0,
            'vmax'      : 1,
            'cmap'      : 'viridis',
            'fmt'       : '{:.2f}',
            })

    # add variable to opts
    opts.update({'variable':variable})

    return opts

if __name__ == '__main__':
    plot_domain_orography()
