import pandas as pd
import networkx as nx
import os

def build_graph(df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed weighted graph from logistics data.

    Args:
        df: Cleaned segment-level DataFrame

    Returns:
        nx.DiGraph object
    """
    print("Building logistics network graph...")
    G = nx.DiGraph()

    # Add nodes with attributes
    # We take the first occurrence of city/state for each center
    node_data = pd.concat([
        df[['source_center', 'src_city', 'src_state']].rename(columns={'source_center': 'center', 'src_city': 'city', 'src_state': 'state'}),
        df[['destination_center', 'dst_city', 'dst_state']].rename(columns={'destination_center': 'center', 'dst_city': 'city', 'dst_state': 'state'})
    ]).drop_duplicates('center')

    for _, row in node_data.iterrows():
        G.add_node(row['center'], 
                   city=str(row['city']) if pd.notna(row['city']) else "Unknown", 
                   state=str(row['state']) if pd.notna(row['state']) else "Unknown")

    # Aggregate edge (corridor) data
    print("Aggregating corridor metrics...")
    
    # Corridor is defined by source_center -> destination_center
    corridors = df.groupby(['source_center', 'destination_center']).agg(
        volume=('trip_uuid', 'count'),
        median_delay_ratio=('delay_ratio', 'median'),
        mean_delay_ratio=('delay_ratio', 'mean'),
        median_actual_time=('segment_actual_time', 'median'),
        median_osrm_time=('segment_osrm_time', 'median'),
        median_distance=('segment_osrm_distance', 'median'),
        n_delayed=('is_delayed', 'sum')
    ).reset_index()

    corridors['pct_delayed'] = corridors['n_delayed'] / corridors['volume']
    corridors['is_chronic'] = (corridors['median_delay_ratio'] > 1.20).astype(int)

    # Route-type specific delays
    ftl_delays = df[df['route_type'] == 'FTL'].groupby(['source_center', 'destination_center'])['delay_ratio'].median()
    carting_delays = df[df['route_type'] == 'Carting'].groupby(['source_center', 'destination_center'])['delay_ratio'].median()

    # Add edges to graph
    for _, row in corridors.iterrows():
        u, v = row['source_center'], row['destination_center']
        
        # Primary weight is median_delay_ratio
        G.add_edge(u, v,
            weight=row['median_delay_ratio'],
            volume=row['volume'],
            median_delay_ratio=row['median_delay_ratio'],
            mean_delay_ratio=row['mean_delay_ratio'],
            median_actual_time=row['median_actual_time'],
            median_osrm_time=row['median_osrm_time'],
            median_distance=row['median_distance'],
            pct_delayed=row['pct_delayed'],
            is_chronic=row['is_chronic'],
            ftl_delay=ftl_delays.get((u, v), 0.0),
            carting_delay=carting_delays.get((u, v), 0.0)
        )

    print(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    chronic_count = sum(1 for _, _, d in G.edges(data=True) if d.get('is_chronic') == 1)
    print(f"Number of chronic corridors: {chronic_count}")

    return G

def save_graph(G: nx.DiGraph, path: str):
    """
    Save graph to GraphML format.

    Args:
        G: NetworkX graph
        path: Output file path
    """
    print(f"Saving graph to {path}...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    nx.write_graphml(G, path)

def load_graph(path: str) -> nx.DiGraph:
    """
    Load graph from GraphML format.

    Args:
        path: Input file path

    Returns:
        nx.DiGraph object
    """
    print(f"Loading graph from {path}...")
    return nx.read_graphml(path)
