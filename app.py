import streamlit as st
import pandas as pd
import networkx as nx
import joblib
import os
import numpy as np
from src.visualise import build_plotly_network
from src.graph_builder import load_graph
from src.eta_model import predict_eta
from src.route_classifier import recommend_route

st.set_page_config(page_title="Delhivery Graph Intelligence", layout="wide")

@st.cache_resource
def load_artifacts():
    """
    Load necessary artifacts for the dashboard.
    """
    try:
        metrics = pd.read_csv('outputs/reports/hub_metrics.csv')
        corridors = pd.read_csv('outputs/reports/corridors.csv')
        G = nx.read_graphml('outputs/models/network_graph.graphml')
        benchmark = pd.read_csv('outputs/reports/model_benchmark.txt', sep=r'\s+', skipinitialspace=True)
        decision_boundary = pd.read_csv('outputs/models/decision_boundary.csv')
        
        # Load models
        models = {
            'baseline': joblib.load('outputs/models/baseline_eta_model.joblib'),
            'graph': joblib.load('outputs/models/graph_enhanced_eta_model.joblib'),
            'route': joblib.load('outputs/models/route_classifier_model.joblib'),
            'embeddings': joblib.load('outputs/models/node_embeddings.joblib')
        }
        
        return metrics, corridors, G, benchmark, decision_boundary, models
    except Exception as e:
        st.error(f"Error loading project artifacts: {e}. Please ensure the pipeline has completed successfully.")
        return None, None, None, None, None, None

def main():
    st.sidebar.title("Delhivery Network Intel")
    page = st.sidebar.radio("Go to", ["Network Overview", "Bottleneck Hub Analysis", "ETA Prediction", "Route Recommender", "Strategy Memo"])

    metrics, corridors, G, benchmark, decision_boundary, models = load_artifacts()
    if metrics is None: return

    if page == "Network Overview":
        st.title("Delhivery Network Intelligence Dashboard")
        
        # KPI Cards
        chronic_pct = (corridors['is_chronic'].mean() * 100)
        avg_delay = corridors['median_delay_ratio'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Hubs", len(G.nodes()))
        col2.metric("Total Corridors", len(G.edges()))
        col3.metric("Chronic Corridors %", f"{chronic_pct:.1f}%")
        col4.metric("Avg Delay Ratio", f"{avg_delay:.2f}")

        st.subheader("Interactive Network Map")
        st.write("Use the controls below to filter the network map and reduce clutter.")
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            min_volume = st.slider("Minimum Corridor Volume", min_value=1, max_value=int(corridors['volume'].max()), value=50, step=10)
        with col_filter2:
            only_chronic = st.checkbox("Show Only Chronic Corridors", value=False)
        with col_filter3:
            color_option = st.selectbox("Color Nodes By", 
                options=['Bottleneck Score', 'Avg Outgoing Delay', 'Total Volume'],
                index=0)
            
        metric_map = {
            'Bottleneck Score': 'bottleneck_score',
            'Avg Outgoing Delay': 'avg_outgoing_delay',
            'Total Volume': 'total_volume'
        }
            
        # Filter Graph
        H = G.copy()
        edges_to_remove = [(u, v) for u, v, d in H.edges(data=True) if d['volume'] < min_volume or (only_chronic and d['is_chronic'] == 0)]
        H.remove_edges_from(edges_to_remove)
        H.remove_nodes_from(list(nx.isolates(H)))
        
        st.info(f"Showing **{H.number_of_nodes()}** hubs and **{H.number_of_edges()}** corridors based on filters.")
        
        fig = build_plotly_network(H, metrics, corridors, color_metric=metric_map[color_option], color_title=color_option)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Bottleneck Hub Analysis":
        st.title("Bottleneck Hub Analysis")
        st.subheader("Top 20 Bottleneck Hubs")
        st.dataframe(metrics.head(20), use_container_width=True)
        
        hub_choice = st.selectbox("Select a Hub for Deep Dive", metrics['hub_id'].unique())
        hub_corridors = corridors[corridors['source'].astype(str) == str(hub_choice)]
        st.subheader(f"Outgoing Corridors for Hub {hub_choice}")
        st.dataframe(hub_corridors, use_container_width=True)

    elif page == "ETA Prediction":
        st.title("ETA Prediction")
        st.table(benchmark)
        
        st.subheader("Predict Trip ETA")
        with st.form("eta_form"):
            col1, col2 = st.columns(2)
            with col1:
                src = st.selectbox("Source Hub", metrics['hub_id'].unique())
                dst = st.selectbox("Destination Hub", metrics['hub_id'].unique())
                dist = st.number_input("Distance (km)", value=150.0)
                osrm_t = st.number_input("OSRM Time (min)", value=200.0)
            with col2:
                hour = st.slider("Trip Hour", 0, 23, 12)
                month = st.slider("Month", 1, 12, 5)
                dow = st.slider("Day of Week (0=Mon, 6=Sun)", 0, 6, 2)
                route = st.selectbox("Route Type", ["FTL", "Carting"])
            
            submit = st.form_submit_button("Predict")
            
        if submit:
            # Prepare feature vector for models
            # Baseline features: osrm_time, osrm_distance, n_segments, trip_hour, trip_dayofweek, trip_month, is_weekend, pct_delayed_segs, route_FTL
            base_data = {
                'osrm_time': osrm_t,
                'osrm_distance': dist,
                'n_segments': 3, # Average segments
                'trip_hour': hour,
                'trip_dayofweek': dow,
                'trip_month': month,
                'is_weekend': dow >= 5,
                'pct_delayed_segs': 0.15,
                'route_FTL': 1 if route == "FTL" else 0,
                'route_Carting': 1 if route == "Carting" else 0
            }
            X_base = pd.DataFrame([base_data])
            
            # Predict
            pred_base = predict_eta(models['baseline'], X_base)[0]
            
            # Graph features
            embeddings = models['embeddings']
            hub_metrics = metrics.set_index('hub_id')
            
            def get_hub_features(hid, prefix):
                emb = embeddings.get(str(hid), np.zeros(32))
                mets = hub_metrics.loc[hid] if hid in hub_metrics.index else pd.Series(0, index=hub_metrics.columns)
                d = {f'{prefix}_n2v_{i}': v for i, v in enumerate(emb)}
                for m in ['betweenness', 'bottleneck_score', 'avg_outgoing_delay', 'clustering', 'pagerank']:
                    d[f'{prefix}_{m}'] = mets.get(m, 0.0)
                return d

            X_graph = X_base.copy()
            src_feats = get_hub_features(src, 'src')
            dst_feats = get_hub_features(dst, 'dst')
            for k, v in {**src_feats, **dst_feats}.items():
                X_graph[k] = v

            # Ensure column order matches model
            X_graph = X_graph[models['graph'].get_booster().feature_names]
            X_base = X_base[models['baseline'].get_booster().feature_names]

            pred_base = predict_eta(models['baseline'], X_base)[0]
            pred_graph = predict_eta(models['graph'], X_graph)[0]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Baseline Prediction", f"{pred_base:.1f} min")
            c2.metric("Graph-Enhanced Prediction", f"{pred_graph:.1f} min", delta=f"{pred_graph - pred_base:.1f} min", delta_color="inverse")
            
            c3.markdown(f"""
            <div style='background-color: #1e1e24; padding: 15px; border-radius: 8px;'>
                <h4 style='margin-top: 0;'>Graph Awareness</h4>
                <p style='color: #00d2ff; font-size: 1.2em;'>Model adjusted ETA by <b>{abs(pred_graph - pred_base):.1f} mins</b> due to hub congestion and structural routing delays.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Simple bar chart comparison
            fig_eta = go.Figure(data=[
                go.Bar(name='Baseline ETA', x=['ETA Model'], y=[pred_base], marker_color='#333'),
                go.Bar(name='Graph-Enhanced ETA', x=['ETA Model'], y=[pred_graph], marker_color='#ff4b4b' if pred_graph > pred_base else '#00ff9d')
            ])
            fig_eta.update_layout(barmode='group', height=300, paper_bgcolor="#0f0f14", plot_bgcolor="#0f0f14", font=dict(color='white'), margin=dict(t=30, b=10))
            st.plotly_chart(fig_eta, use_container_width=True)

    elif page == "Route Recommender":
        st.title("Route Recommender (FTL vs Carting)")
        
        with st.form("route_form"):
            src = st.selectbox("Source Hub", metrics['hub_id'].head(100))
            dist = st.slider("Distance (km)", 0, 1500, 450)
            osrm_t = dist * 1.5 # rough estimate
            hour = st.slider("Trip Hour", 0, 23, 12)
            tod = st.selectbox("Time of Day", ["morning", "afternoon", "evening", "late_night"])
            submit = st.form_submit_button("Analyze")
            
        if submit:
            hub_mets = metrics.set_index('hub_id').loc[src]
            input_data = {
                'osrm_distance': dist,
                'seg_dist_sum': dist,
                'n_segments': 3,
                'osrm_time': osrm_t,
                'trip_hour': hour,
                'is_weekend': False,
                'src_betweenness': hub_mets['betweenness'],
                'src_bottleneck_score': hub_mets['bottleneck_score'],
                'src_avg_outgoing_delay': hub_mets['avg_outgoing_delay'],
                'src_in_degree': hub_mets['in_degree'],
                'src_out_degree': hub_mets['out_degree'],
                'tod_morning': 1 if tod == 'morning' else 0,
                'tod_afternoon': 1 if tod == 'afternoon' else 0,
                'tod_evening': 1 if tod == 'evening' else 0,
                'tod_late_night': 1 if tod == 'late_night' else 0
            }
            input_df = pd.DataFrame([input_data])
            # Ensure column order matches model
            input_df = input_df[models['route'].get_booster().feature_names]
            rec = recommend_route(models['route'], input_df)
            
            st.success(f"Recommendation: **{rec['recommendation']}**")
            
            # Gauge Chart for Confidence
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = rec['confidence'] * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"{rec['recommendation']} Confidence %", 'font': {'size': 20, 'color': 'white'}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': "#00ff9d" if rec['recommendation'] == "FTL" else "#00d2ff"},
                    'bgcolor': "white",
                    'steps': [
                        {'range': [0, 50], 'color': '#333'},
                        {'range': [50, 75], 'color': '#555'},
                        {'range': [75, 100], 'color': '#777'}],
                }
            ))
            fig.update_layout(paper_bgcolor="#0f0f14", font={'color': "white"}, height=300)
            
            col_g1, col_g2 = st.columns([1, 1])
            with col_g1:
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                st.write(f"### Expected Time Saving")
                st.write(f"<h1 style='color: #00ff9d;'>{rec['expected_time_saving_pct']}%</h1>", unsafe_allow_html=True)
                st.info(f"**Reason:** {rec['reason']}")

    elif page == "Strategy Memo":
        st.title("Executive Strategy Memo")
        if os.path.exists('strategy_memo.md'):
            with open('strategy_memo.md', 'r') as f:
                st.markdown(f.read())
        
        st.subheader("Visual Analysis Gallery")
        cols = st.columns(2)
        figs = ["network_bottleneck.png", "top_hubs.png", "chronic_corridors.png", "model_comparison.png"]
        for i, fig in enumerate(figs):
            path = f"outputs/figures/{fig}"
            if os.path.exists(path):
                cols[i % 2].image(path, caption=fig.replace("_", " ").replace(".png", ""))

if __name__ == "__main__":
    main()
