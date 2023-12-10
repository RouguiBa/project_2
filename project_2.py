import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon,MultiPoint
import requests
import os
from shapely.geometry import shape
import pyproj


# Step 1: Read and filter stations from the data files
def read_and_filter_stations(data_path):
    """
    Read and filter station data from fixed-width format files.
    
    Parameters:
    - data_path (str): Path to the directory containing station data files.
    
    Returns:
    - filtered_stations (GeoDataFrame): GeoDataFrame containing filtered station data.
    """
    all_stations = gpd.GeoDataFrame()

    for file_name in os.listdir(data_path):
        if file_name.endswith('.txt'):
            file_path = os.path.join(data_path, file_name)
            try:
                stations = pd.read_fwf(file_path)
                
                stations.columns = ['id', 'name', 'type', 'code', 'x', 'y', 'z', 'dx', 'dy', 'dz']
                
                all_stations = pd.concat([all_stations, stations], ignore_index=True)
            except pd.errors.ParserError as e:
                print(f"Error reading file {file_name}: {e}")

    # Filter stations based on conditions
    filtered_stations = all_stations.groupby(all_stations['id'].str[:5]).filter(lambda x: x['type'].nunique() >= 3)
  
    return filtered_stations


def calculate_and_export_station_polygons(stations, output_path):
    """
    Calculate station polygons based on station coordinates and export as a Shapefile.
    
    Parameters:
    - stations (DataFrame): DataFrame containing station information.
    - output_path (str): Path to the directory for exporting Shapefile.
    
    Returns:
    - None
    """


    stations['geometry'] = stations.apply(lambda row: Point(row['x'], row['y'],row['z']), axis=1)


    # Definition of the original CRS (EPSG:4978)
    original_crs = 'EPSG:4978'

    # Definition of the target CRS (EPSG:4326)
    target_crs = 'EPSG:4326'

    # Creation of a Pyproj transformer
    transformer = pyproj.Transformer.from_crs(original_crs, target_crs, always_xy=True)

    # Use of pyproj for the coordinate transformation
    stations['geometry'] = stations['geometry'].apply(lambda row: Point(transformer.transform(row.x, row.y,row.z)))
    
    # Creation of a GeoDataFrame with the transformed geometries
    stations_gdf = gpd.GeoDataFrame(stations, geometry='geometry', crs=target_crs)

    station_polygons = []

    for _, group in stations_gdf.groupby('id')['geometry']:
        
        if len(group) >= 1:
            # If there is only one coordinate, create a Point geometry
            if len(group) == 1:
                station_polygons.append(group.iloc[0])
            else:
                # If there are more than one coordinate, create a Polygon using buffer
                polygon = MultiPoint(group.tolist()).convex_hull.buffer(0)
                station_polygons.append(polygon)

    # Check if station_polygons is empty
    if not station_polygons:
        print("No valid polygons to export.")
    else:
        station_polygons_gdf = gpd.GeoDataFrame(geometry=station_polygons, crs=target_crs)
        station_polygons_gdf.to_file(os.path.join(output_path, 'station_polygons.shp'))



# Step 4: API request function
def request_images(wkt_geometry, date_1, date_2):
    """
   Perform API request to retrieve satellite images within a specified date range and geometry.
   
   Parameters:
   - wkt_geometry (str): Well-known text representation of the search geometry.
   - date_1 (str): Start date for the search in YYYY-MM-DD format.
   - date_2 (str): End date for the search in YYYY-MM-DD format.
   
   Returns:
   - items (list): List of retrieved image features.
   """
    items = [] # Empty list to store return elements
    url = (
        f"https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json?"
        f"cloudCover=[0,10]"
        f"&startDate={date_1}T00:00:00Z&completionDate={date_2}T23:59:59Z"
        f"&geometry={wkt_geometry}"
    )
    # Request
    r = requests.get(url)#, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    # If status_code is not 200, we have an issue
    if r.status_code == 200:
        data = r.json()
        if 'features' in data:
            items += data['features']
    return items



def list_and_export_images(stations, output_path, start_date, end_date):
    """
    List and export satellite images for each station within a specified date range.
    
    Parameters:
    - stations (GeoDataFrame): GeoDataFrame containing station information.
    - output_path (str): Path to the directory for exporting JSON and Shapefiles.
    - start_date (str): Start date for the image search in YYYY-MM-DD format.
    - end_date (str): End date for the image search in YYYY-MM-DD format.
    
    Returns:
    - None
    """
    images_gdf = gpd.GeoDataFrame()

    for _, station in stations.iterrows():
        wkt_geometry = station['geometry'].buffer(0.1).envelope.wkt  # Buffer for a small area around the station
        
        images = request_images(wkt_geometry, start_date, end_date)

        # Creation of the GeoDataFrame for images
        images_df = gpd.GeoDataFrame(images)
        
        
        # Extraction of the coordinates based on the structure of 'images' object
        images_df['coordinates'] = images_df['geometry'].apply(lambda x: x['coordinates'][0] if 'coordinates' in x else None)
        # Drop rows with missing coordinates
        images_df = images_df.dropna(subset=['coordinates'])

        images_df['geometry'] = images_df['geometry'].apply(lambda x: shape(x))
        images_df['collection'] = images_df['properties'].apply(lambda x: x.get('collection', None))
        images_df['status'] = images_df['properties'].apply(lambda x: x.get('status', None))        
        images_df['station'] = station['id']
        images_gdf = pd.concat([images_gdf, images_df], ignore_index=True)

        # Write temporary JSON file for each station
        os.makedirs('temporary_stations_files', exist_ok=True)

        
        images_df.to_csv(os.path.join('temporary_stations_files', f"{station['id']}.json"))

    # Merge all information into one SHP file
    if not images_gdf.empty:
        images_gdf = images_gdf.set_geometry('geometry')
        
        # Drop the original 'coordinates' column
        images_gdf = images_gdf.drop(columns=['coordinates'])
        
        # Save the GeoDataFrame to a Shapefile
        images_gdf.to_file(os.path.join(output_path, 'images.shp'))



# Main execution
if __name__ == "__main__":
    data_path = "data"
    output_path = "output"
    os.makedirs(output_path, exist_ok=True)
    start_date = "2022-01-01"
    end_date = "2022-09-30"

    print("This code may take a few minutes to run.")

    # Step 1
    filtered_stations = read_and_filter_stations(data_path)

    # Step 2
    calculate_and_export_station_polygons(filtered_stations, output_path)

    # Step 3
    list_and_export_images(filtered_stations, output_path, start_date, end_date)
