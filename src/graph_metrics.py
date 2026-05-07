import pandas as pd
import networkx as nx
import numpy as np
from typing import Tuple

def compute_node_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """
    Compute centrality and bottleneck metrics for all nodes in the graph.

    Args:
        G: NetworkX directed graph

    Returns:
        DataFrame with hub metrics sorted by bottleneck score
    """
    print("Computing node centrality metrics...")
    
    # Centrality measures
    betweenness = nx.betweenness_centrality(G, weight='weight', k=min(500, len(G)))
    pagerank = nx.pagerank(G, weight='weight')
    closeness = nx.closeness_centrality(G)
    clustering = nx.clustering(G.to_undirected())
    
    node_data = []
    for node in G.nodes():
        # In/Out degree
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        
        # Outgoing delays and volumes
        outgoing_edges = G.out_edges(node, data=True)
        avg_outgoing_delay = np.mean([d['median_delay_ratio'] for _, _, d in outgoing_edges]) if outgoing_edges else 1.0
        
        incoming_edges = G.in_edges(node, data=True)
        avg_incoming_delay = np.mean([d['median_delay_ratio'] for _, _, d in incoming_edges]) if incoming_edges else 1.0
        
        total_volume = sum([d['volume'] for _, _, d in G.edges(node, data=True)]) + \
                       sum([d['volume'] for _, _, d in G.in_edges(node, data=True)])
        
        node_data.append({
            'hub_id': node,
            'city': G.nodes[node].get('city', 'Unknown'),
            'state': G.nodes[node].get('state', 'Unknown'),
            'betweenness': betweenness[node],
            'in_degree': in_deg,
            'out_degree': out_deg,
            'degree': in_deg + out_deg,
            'clustering': clustering.get(node, 0),
            'pagerank': pagerank[node],
            'closeness': closeness[node],
            'avg_outgoing_delay': avg_outgoing_delay,
            'avg_incoming_delay': avg_incoming_delay,
            'total_volume': total_volume
        })
    
    df_metrics = pd.DataFrame(node_data)
    
    # Normalize metrics for bottleneck score calculation [0, 1]
    def normalize(series):
        if series.max() == series.min():
            return series * 0
        return (series - series.min()) / (series.max() - series.min())

    print("Calculating composite bottleneck scores...")
    df_metrics['norm_betweenness'] = normalize(df_metrics['betweenness'])
    df_metrics['norm_delay'] = normalize(df_metrics['avg_outgoing_delay'])
    df_metrics['norm_volume'] = normalize(df_metrics['total_volume'])
    df_metrics['norm_in_degree'] = normalize(df_metrics['in_degree'])
    df_metrics['norm_pagerank'] = normalize(df_metrics['pagerank'])
    
    # Bottleneck score formula
    df_metrics['bottleneck_score'] = (
        0.35 * df_metrics['norm_betweenness'] +
        0.25 * df_metrics['norm_delay'] +
        0.20 * df_metrics['norm_volume'] +
        0.10 * df_metrics['norm_in_degree'] +
        0.10 * df_metrics['norm_pagerank']
    )
    
    df_metrics = df_metrics.sort_values(by='bottleneck_score', ascending=False)
    
    print("Top 10 Bottleneck Hubs:")
    print(df_metrics[['hub_id', 'city', 'bottleneck_score', 'total_volume', 'avg_outgoing_delay']].head(10))
    
    return df_metrics

def audit_corridors(G: nx.DiGraph) -> pd.DataFrame:
    """
    Extract edge-level metrics to identify problematic corridors.

    Args:
        G: NetworkX directed graph

    Returns:
        DataFrame of all corridors sorted by delay-volume score
    """
    edge_data = []
    for u, v, d in G.edges(data=True):
        edge_data.append({
            'source': u,
            'destination': v,
            'median_delay_ratio': d['median_delay_ratio'],
            'pct_delayed': d['pct_delayed'],
            'volume': d['volume'],
            'median_actual_time': d['median_actual_time'],
            'median_osrm_time': d['median_osrm_time'],
            'is_chronic': d['is_chronic'],
            'delay_volume_score': d['median_delay_ratio'] * d['volume']
        })
    
    df_corridors = pd.DataFrame(edge_data)
    df_corridors = df_corridors.sort_values(by='delay_volume_score', ascending=False)
    
    chronic_count = df_corridors['is_chronic'].sum()
    print(f"Audited {len(df_corridors)} corridors. Chronic: {chronic_count}")
    
    return df_corridors

def estimate_sla_impact(metrics: pd.DataFrame, corridors: pd.DataFrame, total_delayed_segments: int) -> pd.DataFrame:
    """
    Estimate financial and SLA impact for the top bottleneck hubs.

    Args:
        metrics: Node metrics DataFrame
        corridors: Edge metrics DataFrame
        total_delayed_segments: Total count of delayed segments in the dataset

    Returns:
        Impact analysis DataFrame for top 5 hubs
    """
    top_5 = metrics.head(5).copy()
    
    impact_data = []
    for _, hub in top_5.iterrows():
        hub_id = hub['hub_id']
        
        # Get all corridors starting from this hub
        hub_corridors = corridors[corridors['source'] == hub_id]
        
        # Est SLA breaches = sum(volume * pct_delayed) for outgoing corridors
        est_breaches = (hub_corridors['volume'] * hub_corridors['pct_delayed']).sum()
        pct_of_total = est_breaches / total_delayed_segments if total_delayed_segments > 0 else 0
        revenue_at_risk = est_breaches * 350 # ₹350 per failed delivery assumption
        
        impact_data.append({
            'hub_id': hub_id,
            'city': hub['city'],
            'state': hub['state'],
            'bottleneck_score': hub['bottleneck_score'],
            'estimated_sla_breaches': int(est_breaches),
            'pct_of_total_breaches': pct_of_total,
            'revenue_at_risk_inr': revenue_at_risk
        })
        
    return pd.DataFrame(impact_data)
