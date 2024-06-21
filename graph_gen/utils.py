import osmnx as ox
from collections import Counter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def add_missing_spd(G):
    """
    Add missing speed limits to edges in the graph based on the most common speed for each highway type.
    If no data for the highway type is available, most common speed is picked.
    
    Args:
    - G (osmnx.MultiDiGraph): Graph to extend with missing speed limits.
    
    Returns:
    - G (osmnx.MultiDiGraph): The graph with missing speed limits added.
    """
    highwayspds = {}
    all_speeds = []
    
    for edge in G.edges:
        highway_type = G.edges[edge].get('highway')
        if 'maxspeed' in G.edges[edge]:
            if highway_type not in highwayspds:
                highwayspds[highway_type] = []
            speed = G.edges[edge]['maxspeed']
            highwayspds[highway_type].append(speed)
            all_speeds.append(speed)
    
    most_common_speed_dict = {road_type: most_common_speed(speeds) for road_type, speeds in highwayspds.items()}
    general_most_common_speed = most_common_speed(all_speeds)
    
    for edge in G.edges:
        if 'maxspeed' not in G.edges[edge]:
            highway_type = G.edges[edge].get('highway')
            selected_spd = most_common_speed_dict.get(highway_type, general_most_common_speed)
            G.edges[edge]['maxspeed'] = selected_spd

    return G

def spd_ox2bs(G):
    """
    Add a new attribute 'maxspeed_kts' to each edge in the graph based on the 'maxspeed' attribute.
    This must be used in Bluesky, values have to be in kts.
    
    Args:
    - G (osmnx.MultiDiGraph): Graph to extend with Bluesky Speed.
    
    Returns:
    - G (osmnx.MultiDiGraph): The graph with the additional 'maxspeed_kts' attribute.
    """
    for u, v, k, data in G.edges(keys=True, data=True):
        maxspeed = data.get('maxspeed', None)
        if maxspeed is not None:
            maxspeed_kts = spdlim_ox2bs(maxspeed)
            data['maxspeed_kts'] = maxspeed_kts
        else:
            raise AttributeError(f"Something went wrong, attribute maxspeed not found for edge {u, v}")

    return G

def spdlim_ox2bs(spdlim):
    """
    Convert speed limit to knots.
    When no value is given, value is in kph:
    https://wiki.openstreetmap.org/wiki/Key:maxspeed
    Otherwise, value is in mph.
    
    Args:
    - spdlim (str, int, or float): Speed limit in various formats.
    
    Returns:
    - float: Speed limit in knots.
    
    Raises:
    - TypeError: If the type of spdlim is not recognized.
    """
    if type(spdlim) == str and 'mph' in spdlim:
        try:
            spdlim = int(spdlim.strip('mph'))
        except ValueError:
            # ValueError occurs when there is a double entry for spd limit
            # Take the highest one
            spdlim = max([int(s.strip().replace(' mph', '')) for s in spdlim.split(',')])
        # Value is in mph so convert from mph to kts
        spdlim = mph2kts(spdlim)
    elif type(spdlim) in [float, int]:
        spdlim = kph2kts(spdlim)
    elif type(spdlim) == str:
        # kph value is given in str format
        # split the value in case more values are given
        spdlim = kph2kts(spdlim.rsplit(',')[-1])
    else:
        raise TypeError("Undefined type for speedlimit")

    return spdlim

def most_common_speed(speed_list):
    """
    Get the most common speed from a list of speeds.
    
    Args:
    - speed_list (list): List of speed values.
    
    Returns:
    - int: Most common speed in the list.
    """
    return Counter(speed_list).most_common(1)[0][0]

def simplify_graph(G, tol=0.0001, gpkg_file=False):
    """
    Simplify the geometries of the edges in the GeoDataFrame.
    
    Args:
    - G (osmnx.MultiDiGraph): Graph containing the edges to be simplified.
    - tol (float): The simplification tolerance. Default is 0.0001.
    - gpkg_file (bool): Whether to save the original and simplified edges to a GPKG file for inspection. Default is False.
    
    Returns:
    - G (osmnx.MultiDiGraph): Graph with simplified geometries.
    """
    # Convert the graph to GeoDataFrames
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

    # Identify and handle list-type fields
    list_type_columns = [col for col in gdf_edges.columns if gdf_edges[col].apply(lambda x: isinstance(x, list)).any()]
    # Convert list-type columns to strings
    for col in list_type_columns:
        gdf_edges[col] = gdf_edges[col].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else x)

    gdf_edges_simplified = gdf_edges.copy()
    simplified_geometries = gdf_edges_simplified['geometry'].apply(lambda geom: geom.simplify(tol, preserve_topology=True))
    gdf_edges_simplified['geometry'] = simplified_geometries
    
    if gpkg_file:
        # Save the edges and nodes to a gpkg file for closer inspection on the simplifcation.
        # This has already been performed for tol=0.0001 (default), which gives accurate results but also faster 
        # processing of scenarios and simulation
        gdf_edges.to_file("graph_comparison.gpkg", layer='original_edges', driver="GPKG")
        gdf_edges_simplified.to_file("graph_comparison.gpkg", layer=f'edges {tol}', driver="GPKG")
        gdf_nodes.to_file("graph_comparison.gpkg", layer='nodes', driver="GPKG")

    # Convert back to an OSMNX graph
    G_mod = ox.graph_from_gdfs(gdf_nodes, gdf_edges_simplified)

    return G_mod

def mph2kts(mph):
    """
    Convert speed in mph to knots.
    
    Args:
    - mph (float): Speed in miles per hour.
    
    Returns:
    - float: Speed in knots.
    """
    return float(mph) * 0.868976242

def kph2kts(kph):
    """
    Convert speed in kph to knots.
    
    Args:
    - kph (float): Speed in km per hour.
    
    Returns:
    - float: Speed in knots.
    """
    return float(kph) * 0.539956803

class CityNotFoundError(Exception):
    """
    Custom exception for cases where the city cannot be found.
    """
    pass

def get_city_from_bbox(north, south, east, west):
    """
    Get the city name based on the bounding box limits.

    Parameters:
    - north (float): Northern latitude of the bounding box.
    - south (float): Southern latitude of the bounding box.
    - east (float): Eastern longitude of the bounding box.
    - west (float): Western longitude of the bounding box.

    Returns:
    - str: The name of the city.

    Raises:
    - CityNotFoundError: If the city cannot be determined.
    - Exception: For geocoding service errors.
    """
    geolocator = Nominatim(user_agent="my_geopy_application")
    
    # Calculate the center point of the bounding box
    center_lat = (north + south) / 2
    center_lon = (east + west) / 2

    try:
        # Reverse geocode using the center point of the bounding box
        location = geolocator.reverse((center_lat, center_lon), exactly_one=True)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        raise Exception(f"Geocoding service error: {e}")

    if location and location.raw:
        address = location.raw.get('address', {})
        city = address.get('city') or address.get('town') or address.get('village') or address.get('county')
        if city:
            return city
    
    raise CityNotFoundError("City could not be determined from the bounding box limits.")
