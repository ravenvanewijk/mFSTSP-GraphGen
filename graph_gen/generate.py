from .utils import add_missing_spd, simplify_graph, get_city_from_bbox, add_spds
import osmnx as ox
import argparse
import os

def generate_graph(north, south, east, west):
    """
    Generate and save an OSM graph based on bounding box limits.

    Parameters:
    north (float): Northern latitude of the bounding box.
    south (float): Southern latitude of the bounding box.
    east (float): Eastern longitude of the bounding box.
    west (float): Western longitude of the bounding box.

    Returns:
    str: Path to the saved graph file.
    """
    lims = (north, south, east, west)
    G = ox.graph_from_bbox(bbox=lims, network_type='drive')
    city = get_city_from_bbox(north, south, east, west)
    G = simplify_graph(G)
    G = add_missing_spd(G)
    G = add_spds(G)
    G = ox.routing.add_edge_travel_times(G)
    graph_file = f'{city}.graphml'
    ox.save_graphml(G, graph_file)
    return graph_file

def main():
    parser = argparse.ArgumentParser(description="Generate OSM graph for a given place.")
    parser.add_argument('north', type=float, help="Latitude of most northern point")
    parser.add_argument('south', type=float, help="Latitude of most southern point")
    parser.add_argument('east', type=float, help="Longitude of most eastern point")
    parser.add_argument('west', type=float, help="Longitude of most western point")

    args = parser.parse_args()
    generate_graph(args.north, args.south, args.east, args.west)

if __name__ == "__main__":
    main()

# # Example usage for testing
# generate_graph(43.03392544699964, 42.81679855300036, -78.67067714771929, -78.9389038522807)
