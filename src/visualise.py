import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
import os

# Set style
plt.style.use('dark_background')
BG_COLOR = "#0f0f14"

def plot_network(G: nx.DiGraph, metrics: pd.DataFrame, corridors: pd.DataFrame):
    """
    Plot the logistics network with bottleneck annotations.
    """
    print("Plotting network bottleneck map...")
    fig, ax = plt.subplots(figsize=(15, 12), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    pos = nx.spring_layout(G, k=0.15, seed=42)
    
    # Node metrics
    node_metrics = metrics.set_index('hub_id')
    
    # Node sizes based on betweenness
    sizes = [node_metrics.loc[n, 'betweenness'] * 5000 + 50 for n in G.nodes()]
    
    # Node colors based on bottleneck score
    colors = [node_metrics.loc[n, 'bottleneck_score'] for n in G.nodes()]
    
    # Edges
    chronic_edges = [(u, v) for u, v, d in G.edges(data=True) if d['is_chronic'] == 1]
    normal_edges = [(u, v) for u, v, d in G.edges(data=True) if d['is_chronic'] == 0]
    
    # Edge widths based on volume
    def get_width(u, v):
        vol = G.edges[u, v]['volume']
        return np.log1p(vol) * 0.5

    # Draw normal edges
    nx.draw_networkx_edges(G, pos, edgelist=normal_edges, 
                           width=[get_width(u, v) for u, v in normal_edges],
                           edge_color='#333333', alpha=0.3, ax=ax, arrows=False)
    
    # Draw chronic edges
    nx.draw_networkx_edges(G, pos, edgelist=chronic_edges, 
                           width=[get_width(u, v) for u, v in chronic_edges],
                           edge_color='red', alpha=0.6, ax=ax, arrows=True, arrowsize=10)
    
    # Draw nodes
    nodes = nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=colors, 
                                   cmap=plt.cm.RdYlBu_r, alpha=0.8, ax=ax)
    
    # Labels for top 20 nodes
    top_20 = metrics.head(20)['hub_id'].tolist()
    labels = {n: node_metrics.loc[n, 'city'] for n in top_20}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_color='white', font_weight='bold')

    plt.colorbar(nodes, label='Bottleneck Score', ax=ax)
    ax.set_title("Delhivery Logistics Network — Bottleneck Hubs & Chronic Corridors", 
                 color='white', fontsize=18, pad=20)
    
    os.makedirs('outputs/figures', exist_ok=True)
    plt.savefig('outputs/figures/network_bottleneck.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_delay_distributions(df: pd.DataFrame):
    """
    2-panel plot of delay ratio by route type and time of day with breach zone shading.
    """
    print("Plotting delay distributions...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), facecolor=BG_COLOR)
    
    # Panel 1: Route Type
    sns.kdeplot(data=df, x='delay_ratio', hue='route_type', fill=True, ax=ax1, palette='viridis')
    ax1.axvline(1.2, color='red', linestyle='--', alpha=0.8, label='SLA Threshold (1.2x)')
    # Shade Breach Zone
    ax1.axvspan(1.2, 10, color='red', alpha=0.1, label='SLA Breach Zone')
    ax1.set_title("Delay Ratio Distribution by Route Type\n(Values > 1.2 indicate late deliveries)", color='white', fontsize=14)
    ax1.set_xlabel("Delay Ratio (Actual Time / OSRM Time)")
    ax1.legend()

    # Panel 2: Time of Day
    sns.kdeplot(data=df, x='delay_ratio', hue='time_of_day', fill=True, ax=ax2, palette='magma')
    ax2.axvline(1.2, color='red', linestyle='--', alpha=0.8)
    ax2.axvspan(1.2, 10, color='red', alpha=0.1)
    ax2.set_title("Delay Ratio Distribution by Time of Day\n(Morning vs Evening performance)", color='white', fontsize=14)
    ax2.set_xlabel("Delay Ratio (Actual Time / OSRM Time)")

    plt.tight_layout()
    plt.savefig('outputs/figures/delay_distributions.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_top_hubs(metrics: pd.DataFrame, top_n=15):
    """
    Horizontal bars for top bottleneck hubs with standardized coloring.
    """
    print("Plotting top bottleneck hubs...")
    top_df = metrics.head(top_n).copy()
    top_df['hub_city'] = top_df['city'] + " (" + top_df['hub_id'].astype(str) + ")"
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 9), facecolor=BG_COLOR)
    
    sns.barplot(data=top_df, y='hub_city', x='bottleneck_score', palette='Reds_r', ax=ax1, hue='hub_city', legend=False)
    ax1.set_title("Bottleneck Priority Score\n(Composite risk metric)", color='white', fontsize=12)
    ax1.set_xlabel("Score [0-1]")
    
    sns.barplot(data=top_df, y='hub_city', x='betweenness', palette='YlOrBr_r', ax=ax2, hue='hub_city', legend=False)
    ax2.set_title("Betweenness Centrality\n(Network dependency)", color='white', fontsize=12)
    ax2.set_ylabel("")
    ax2.set_xlabel("Centrality Score")
    
    sns.barplot(data=top_df, y='hub_city', x='avg_outgoing_delay', palette='Oranges_r', ax=ax3, hue='hub_city', legend=False)
    ax3.set_title("Avg Outgoing Delay\n(Hub-level congestion)", color='white', fontsize=12)
    ax3.set_ylabel("")
    ax3.set_xlabel("Mean Delay Ratio")

    plt.suptitle("Top Bottleneck Hub Analysis: Focus for Immediate Intervention", color='white', fontsize=20, y=1.05)
    plt.tight_layout()
    plt.savefig('outputs/figures/top_hubs.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_chronic_corridors(corridors: pd.DataFrame):
    """
    Scatter plot of volume vs delay with quadrant analysis.
    """
    print("Plotting chronic corridors...")
    plt.figure(figsize=(12, 9), facecolor=BG_COLOR)
    ax = plt.gca()
    ax.set_facecolor(BG_COLOR)
    
    # Quadrant logic
    med_vol = corridors['volume'].median()
    
    sns.scatterplot(data=corridors, x='volume', y='median_delay_ratio', 
                    size='delay_volume_score', hue='is_chronic', 
                    palette={1: '#ff4b4b', 0: '#00d2ff'}, alpha=0.6, sizes=(40, 600))
    
    plt.xscale('log')
    plt.axhline(1.2, color='white', linestyle='--', alpha=0.5)
    plt.axvline(med_vol, color='white', linestyle=':', alpha=0.3)
    
    # Annotate Quadrants
    plt.text(corridors['volume'].max()*0.2, 1.25, "CRITICAL: High Volume & High Delay", color='#ff4b4b', fontsize=10, fontweight='bold')
    plt.text(corridors['volume'].min()*1.5, 1.25, "INEFFICIENT: Low Volume but High Delay", color='orange', fontsize=10)
    plt.text(corridors['volume'].max()*0.2, 0.9, "STABLE: High Volume / Reliable", color='#00ff9d', fontsize=10)

    # Annotate top 8
    top_8 = corridors.head(8)
    for _, row in top_8.iterrows():
        plt.annotate(f"{row['source']}->{row['destination']}", 
                     (row['volume'], row['median_delay_ratio']),
                     xytext=(5, 5), textcoords='offset points', color='white', fontsize=8)

    plt.title("Corridor Performance Analysis: Volume vs Reliability Matrix", color='white', fontsize=18, pad=20)
    plt.xlabel("Log(Trip Volume)", fontsize=12)
    plt.ylabel("Median Delay Ratio (SLA Target = 1.0)", fontsize=12)
    
    plt.savefig('outputs/figures/chronic_corridors.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_model_comparison(baseline_results: dict, graph_results: dict):
    """
    Comparison bar chart for models.
    """
    print("Plotting model comparison...")
    b = baseline_results['metrics']
    g = graph_results['metrics']
    
    df_plot = pd.DataFrame({
        'Metric': ['MAE (min)', 'MAE (min)', 'Accuracy within 15%', 'Accuracy within 15%'],
        'Model': ['Baseline', 'Graph-Enhanced', 'Baseline', 'Graph-Enhanced'],
        'Value': [b['mae'], g['mae'], b['within_15pct']*100, g['within_15pct']*100]
    })
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG_COLOR)
    
    sns.barplot(data=df_plot[df_plot['Metric'] == 'MAE (min)'], x='Metric', y='Value', hue='Model', ax=ax1)
    ax1.set_title("Lower is Better", color='white')
    
    sns.barplot(data=df_plot[df_plot['Metric'] == 'Accuracy within 15%'], x='Metric', y='Value', hue='Model', ax=ax2)
    ax2.set_title("Higher is Better (%)", color='white')
    
    plt.savefig('outputs/figures/model_comparison.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_feature_importances(route_classifier_results: dict):
    """
    Feature importance for route classifier.
    """
    print("Plotting feature importances...")
    importances = route_classifier_results['feature_importances'].head(15)
    
    plt.figure(figsize=(10, 8), facecolor=BG_COLOR)
    
    # Assign colors by group
    colors = ['purple' if 'src_' in f or 'dst_' in f else 'blue' for f in importances['feature']]
    
    sns.barplot(data=importances, x='importance', y='feature', palette=colors)
    plt.title("Top 15 Features: FTL vs Carting Classifier", color='white')
    
    plt.savefig('outputs/figures/feature_importances.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def plot_ftl_decision_boundary(decision_boundary_df: pd.DataFrame):
    """
    Heatmap of recommendations.
    """
    print("Plotting decision boundary heatmap...")
    pivot_df = decision_boundary_df.pivot(index='dist_band', columns='time_of_day', values='avg_saving_pct')
    
    plt.figure(figsize=(10, 6), facecolor=BG_COLOR)
    sns.heatmap(pivot_df, annot=True, fmt=".1%", cmap='RdYlGn', cbar_kws={'label': 'Expected FTL Time Saving (%)'})
    plt.title("FTL Recommendation Strategy (Distance vs Time)", color='white')
    
    plt.savefig('outputs/figures/ftl_decision_boundary.png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()

def build_plotly_network(G: nx.DiGraph, metrics: pd.DataFrame, corridors: pd.DataFrame, color_metric='bottleneck_score', color_title='Bottleneck Score') -> go.Figure:
    """
    Interactive Plotly network graph.
    """
    # Handle empty graph
    if G.number_of_nodes() == 0:
        return go.Figure().update_layout(title="No data matches selected filters", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, font=dict(color='white'))

    # Ensure hub_id is string to match G.nodes
    metrics = metrics.copy()
    metrics['hub_id'] = metrics['hub_id'].astype(str)
    node_metrics = metrics.set_index('hub_id')
    
    pos = nx.spring_layout(G, k=0.15, seed=42)
    
    # Edges
    # Separate edges
    chronic_edges = [(u, v) for u, v, d in G.edges(data=True) if d['is_chronic'] == 1]
    normal_edges = [(u, v) for u, v, d in G.edges(data=True) if d['is_chronic'] == 0]

    def create_edge_trace(edge_list, color, width):
        edge_x, edge_y = [], []
        for u, v in edge_list:
            if u in pos and v in pos:
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
        return go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=width, color=color),
            hoverinfo='none',
            mode='lines')

    normal_trace = create_edge_trace(normal_edges, '#333', 0.5)
    chronic_trace = create_edge_trace(chronic_edges, 'red', 1.0)

    # Edge hover markers
    middle_node_x, middle_node_y, middle_node_text = [], [], []
    for u, v, d in G.edges(data=True):
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            middle_node_x.append((x0 + x1) / 2)
            middle_node_y.append((y0 + y1) / 2)
            status = "🔴 <b>CHRONIC DELAY</b>" if d['is_chronic'] else "🟢 <b>STABLE</b>"
            text = (f"<b>Corridor:</b> {u} → {v}<br>"
                    f"<b>Volume:</b> {d['volume']} trips<br>"
                    f"<b>Avg Delay Ratio:</b> {d['median_delay_ratio']:.2f}x<br>"
                    f"<b>Status:</b> {status}")
            middle_node_text.append(text)

    edge_hover_trace = go.Scatter(
        x=middle_node_x, y=middle_node_y,
        text=middle_node_text,
        mode='markers',
        hoverinfo='text',
        marker=dict(size=0.1, color='rgba(0,0,0,0)'))

    # Nodes
    node_x, node_y = [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    # Calculate node sizes safely
    try:
        betweenness_values = [node_metrics.loc[str(n), 'betweenness'] if str(n) in node_metrics.index else 0 for n in G.nodes()]
        max_b = max(betweenness_values) if betweenness_values and max(betweenness_values) > 0 else 1
        node_sizes = [(b / max_b) * 40 + 10 for b in betweenness_values]
    except Exception:
        node_sizes = [15] * len(G.nodes())

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlOrRd',
            reversescale=False,
            color=[],
            size=node_sizes,
            colorbar=dict(
                thickness=15,
                title=dict(text=color_title, side='right'),
                xanchor='left'
            ),
            line_width=1,
            line_color='white'))

    node_adjacencies = []
    node_text = []
    for node in G.nodes():
        node_str = str(node)
        if node_str in node_metrics.index:
            m = node_metrics.loc[node_str]
            text = (f"<b>Hub ID:</b> {node_str}<br>"
                    f"<b>Location:</b> {m['city']}, {m['state']}<br>"
                    f"<b>Bottleneck Score:</b> {m['bottleneck_score']:.3f}<br>"
                    f"<b>Network Degree:</b> {m.get('degree', 'N/A')}<br>"
                    f"<b>Avg Outgoing Delay:</b> {m['avg_outgoing_delay']:.2f}x<br>"
                    f"<b>Total Volume:</b> {m['total_volume']:.0f}")
            node_text.append(text)
            node_adjacencies.append(m.get(color_metric, 0))
        else:
            node_text.append(f"<b>Hub ID:</b> {node_str}")
            node_adjacencies.append(0)

    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text

    # Dynamic subtitle based on selection
    subtitle = f"Red lines = Chronic Delays | Hub Size = Routing Centrality | Color = {color_title}"
    
    fig = go.Figure(data=[normal_trace, chronic_trace, edge_hover_trace, node_trace],
                 layout=go.Layout(
                    title=dict(text=f'<b>Delhivery Logistics Network Explorer</b><br><span style="font-size: 12px; color: #ccc;">{subtitle}</span>', font=dict(size=20)),
                    showlegend=False,
                    hovermode='closest',
                    height=700,
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    paper_bgcolor=BG_COLOR,
                    plot_bgcolor=BG_COLOR,
                    font=dict(color='white')
                ))
    return fig
