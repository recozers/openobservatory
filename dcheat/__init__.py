"""dcheat — estimating data-centre heat rejection from public thermal imagery.

Modules
-------
geom        site polygons, background annulus, rasterisation helpers
landsat_c1  Landsat 8 Collection 1 Level-1 thermal (brightness temperature) from
            the public Google Cloud archive — the backend that runs without
            credentials (2013–2021 only)
gee         Landsat 8/9 Collection 2 Level-2 surface temperature and ERA5-Land
            via Google Earth Engine — the backend specified for the project;
            needs an authenticated `earthengine` client
worldcover  ESA WorldCover 10 m land cover for annulus masking
era5        ERA5 hourly single-level reanalysis from the NCAR mirror on AWS
met         derived meteorology (wind speed, specific humidity, wet-bulb)
"""

__version__ = "0.1.0"
