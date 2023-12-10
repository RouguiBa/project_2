# project_2
GDM_Project
# GIS Project "ITRF2020"

The International Terrestrial Reference Frame (ITRF) is computed from geodetic data collected at observatories all over the world. The coordinates of the permanent instruments at those sites are quality controlled thanks to the availability of the relative position of these instruments determined with standard surveying techniques. Unfortunately, those observations are expensive and rarely repeated. A working group of the International Association of Geodesy is questioning the use of InSAR technology to monitor the relative displacements of the instruments at those sites.

InSAR analysis is a specific processing that makes use of Synthetic Aperture Radar (SAR) space images of the same area to compute a deformation map with mm/yr accuracy. During the lifetime of a SAR satellite, many SAR images are acquired around the world as a function of the user needs. Thus, we would like to make the inventory of  all SAR images collected from Sentinel 1A and Sentinel 1B satellites that cover each ITRF site in order to investigate if deformation maps could be processed. Indeed, at least 12 images of the same area acquired from the same acquisition geometry (same “relative orbit number”) are required to obtain reliable InSAR results.

We focus on ITRF sites that include at least 2 instruments from 2 different measurement techniques (GNSS, DORIS, SLR or VLBI). Two stations are located on the same site if their DOMES number (ID number of the station) starts with the same 5 numbers.

The objective of this project is to collect and map the footprints all Sentinel 1A and Sentinel 1B satellites that cover ITRF sites that verify the above conditions and integrate them in a GIS project for further analyses.

![Stations, Instruments and Image footprints](img/presentation.png)

## Objectives

The objectif of the projet is to make a Python script to read the position of the ITRF stations in the given files (see [data](data) directory) and interrogate an API to list and download the satellite images over theses station.

We would like as output:
* a SHP with the instrument of the processed stations ;
* a SHP with the extent of the stations ;
* a SHP with the extent of the satellite images to download.

## Data

The [data](data) are 4 textual files with :
* id of the station and id of the instrument in this station (`12345S123` : `12345` + `S123`) ;
* name of the station ;
* type of the instrument ;
* name of the instrument ;
* x position ;
* y position ;
* z position ;
* the x-y-z precision.

Example (`ITRF2020_DORIS_cart.txt`):

```txt
id        name            type  code x             y             z             dx     dy     dz
10002S018 Grasse (OCA)    DORIS GR3B  4581680.3279   556166.4818  4389371.6042 0.0020 0.0025 0.0020
10002S019 Grasse (OCA)    DORIS GR4B  4581681.0445   556166.9141  4389370.9730 0.0019 0.0024 0.0017
10003S001 Toulouse        DORIS TLSA  4628047.2485   119670.6873  4372788.0168 0.0054 0.0062 0.0051
10003S003 Toulouse        DORIS TLHA  4628693.4610   119985.0770  4372104.5078 0.0034 0.0042 0.0032
10003S005 Toulouse        DORIS TLSB  4628693.6567   119985.0787  4372104.7202 0.0026 0.0039 0.0025
10077S002 Ajaccio         DORIS AJAB  4696990.0906   723981.2094  4239679.2709 1.2860 1.2898 1.2857
10202S001 Reykjavik       DORIS REYA  2585527.8355 -1044368.1434  5717159.1052 0.0148 0.0163 0.0090
```

## Project statement

1. Open the 4 files and keep only the stations that belongs to a site (look at the five first numbers of the DOMES (id) number) which hosts at least 3 instruments from 2 different measurement techniques (GNSS, DORIS, SLR or VLBI).
2. Calculate for each station the polygon of its extent (convex envelope) and export it as a SHP file (convert geometry from EPSG:4978 to EPSG:4326 at the begining).
3. List for each station the images (between 2022/01/01 and 2022/09/30) that are covering the extent and export it as a SHP file:
    1. For each station, write a `<station_id>.json` temporary file when you do the API request;
    2. Merge all information in one SHP file after.


## API Access

Register : https://scihub.copernicus.eu/dhus/#/self-registration

Make a request like it:

```py
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

# Configuration
USERNAME = "username"
PASSWORD = "password"
NB_ITEMS = 100

def request_images(wkt_geometry, date_1, date_2):
    items = [] # Empty list to store return elements
    start_position = 0 # You will need a while loop
    url = (
        f"https://scihub.copernicus.eu/dhus/search?start={start_position}&rows={NB_ITEMS}&q="
        f'footprint:"Intersects({wkt_geometry})"'
        f" AND (beginPosition:[{date_1}T00:00:00.000Z TO {date_2}T23:59:59.999Z]"
        f" AND endPosition:[{date_1}T00:00:00.000Z TO {date_2}T23:59:59.999Z])"
        f" AND ( (platformname:Sentinel-1 AND producttype:SLC))&format=json"
    )
    # Request
    r = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    # If status_code is not 200, we have an issue
    if r.status_code == 200:
        data = r.json()
        if 'feed' in data and 'entry' in data['feed']:
            # Add items to the list
            new_items = data['feed']['entry']
            if isinstance(new_items, list): # several returned items
                items = items + data['feed']['entry']
            elif isinstance(new_items, dict): # one returned item
                items.append(new_items)
    return items

wkt_geometry = 'POLYGON((2.349250 48.8535,2.348703 48.85293,2.350430 48.8524,2.35091 48.8530,2.349250 48.8535))'
images = request_images(wkt_geometry, datetime(2020, 1, 1).date(), datetime(2020, 1, 31).date())
```

Look at the [data/response_example.json](data/response_example.json) file to have a look at the API response.

You will need to do several request if there are more images than the number of rows you ask (while loop).


## Data help

Instrument SHP:
* geometry type: point (X,Y of the instruments) ;
* `id`: full id of the instrument ;
* `name`: name of the station ;
* `type`: type of the instrument (DORIS / GNSS / SLR / VLBI) ;
* `station`: id of the station (first 5 chars of the full id) ;
* `instrument`: id of the instrument (last 4 chars of the full id) ;

Station SHP:
* geometry type: polygon (extent around the instruments)
* `station`: id of the station ;
* `name`: name of the station ;

Images SHP:
* geometry type: polygone (extent of the images)
* `station`: id of the station ;
* `id`: id of the image ;
* `title`: title of the image ;
* `quick_look`: url of the quick look image ;
* `url`: url to download the image ;
* `filename`: filename ;
* `ron`: relative orbit number ;
* `mode`: sensor operational mode ;
* `orbit`: orbit direction (ASCENDING / DESCENDING) ;
* `platform`: platform identifier.
