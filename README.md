# RNS_Sydney_bushfire
Impact of megafires on weather

## Contributions
- Mathew Lipson: ancillary generation, initial model runs
- Abby Smyth: final model runs, analysis

## Configuration

Model: ACCESS-rAM (with OSTIA varying sea surface temperature)  
Model suite: https://code.metoffice.gov.uk/trac/roses-u/browser/d/r/2/1/6/trunk  
Period: 20200114T0000Z to 20200212T0000Z (30 days)  

Domain:
- Outer: GAL9 at 0.11° (~12.2 km) (BARRA-R2 initialised)
- Inner: RAL3p2 at 0.198° (~2.2km at equator)

![Domains](./ancils/Bluemountains_domains_surface_altitude.png)

## Ancillaries

Use u-dg767 with [this optional file](./ancils/rose-suite-rns_bluemountains.conf).
More info here: https://github.com/21centuryweather/RNS_Sydney_bushfire/tree/main/ancils

## Compute

|          | y_npts | x_npts | nproc | CPUS | SU/6hrs  | walltime/6hrs  |
|----------|--------|--------|-------|------|----------|----------------|
| d11000   | 300    | 300    | 16x12 | 192  | 12       | 2 mins         |
| d0198    | 450    | 450    | 24x24 | 576  | 112      | 6 mins         |

### Total per day

- ~500 SU per day
- ~30 min walltime per day

## Experiments

Description of experiments