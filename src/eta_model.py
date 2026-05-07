import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from node2vec import Node2Vec
import networkx as nx
import joblib
import os
from typing import Dict, Tuple

RANDOM_STATE = 42

def train_baseline(df_trip: pd.DataFrame) -> Dict:
    """
    Train a baseline XGBoost model for ETA prediction.

    Args:
        df_trip: Trip-level DataFrame

    Returns:
        Dictionary with model, metrics, and test data
    """
    print("Training baseline ETA model...")
    
    # Feature selection
    features = [
        'osrm_time', 'osrm_distance', 'n_segments', 'trip_hour', 
        'trip_dayofweek', 'trip_month', 'is_weekend', 'pct_delayed_segs'
    ]
    
    X = df_trip[features].copy()
    
    # One-hot encode route_type
    route_dummies = pd.get_dummies(df_trip['route_type'], prefix='route')
    X = pd.concat([X, route_dummies], axis=1)
    
    y = df_trip['actual_time']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=df_trip['route_type'], random_state=RANDOM_STATE
    )
    
    model = xgb.XGBRegressor(
        n_estimators=300, 
        learning_rate=0.05,
        max_depth=6, 
        subsample=0.8, 
        colsample_bytree=0.8,
        random_state=RANDOM_STATE
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    # Evaluation
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # within_15pct: fraction of predictions within 15% of actual
    # Avoid division by zero
    mask = y_test != 0
    accuracy_15pct = np.mean(np.abs((y_test[mask] - y_pred[mask]) / y_test[mask]) <= 0.15)
    
    print(f"Baseline Results: MAE={mae:.2f}, RMSE={rmse:.2f}, Within 15% Accuracy={accuracy_15pct:.2%}")
    
    return {
        'model': model,
        'predictions': y_pred,
        'metrics': {'mae': mae, 'rmse': rmse, 'within_15pct': accuracy_15pct},
        'X_test': X_test,
        'y_test': y_test,
        'test_indices': X_test.index
    }

def train_graph_model(df_trip: pd.DataFrame, metrics: pd.DataFrame, G: nx.DiGraph) -> Dict:
    """
    Train an ETA model enhanced with graph metrics and node2vec embeddings.

    Args:
        df_trip: Trip-level DataFrame
        metrics: Node metrics DataFrame
        G: NetworkX graph

    Returns:
        Dictionary with model, metrics, and test data
    """
    print("Training graph-enhanced ETA model...")
    
    # 1. Generate node2vec embeddings
    print("Generating node2vec embeddings (this may take a minute)...")
    # Note: Using small dimensions and walks for performance as per instructions
    node2vec = Node2Vec(G, dimensions=32, walk_length=20, num_walks=100, p=1, q=1, workers=4, seed=RANDOM_STATE)
    n2v_model = node2vec.fit(window=5, min_count=1, batch_words=4)
    
    def get_embedding(node_id):
        try:
            return n2v_model.wv[str(node_id)]
        except KeyError:
            return np.zeros(32)

    # 2. Attach node features to trips
    print("Attaching graph features to trip data...")
    
    # Node2vec embeddings for source and destination
    src_embeddings = np.array([get_embedding(nid) for nid in df_trip['source_center']])
    dst_embeddings = np.array([get_embedding(nid) for nid in df_trip['destination_center']])
    
    for i in range(32):
        df_trip[f'src_n2v_{i}'] = src_embeddings[:, i]
        df_trip[f'dst_n2v_{i}'] = dst_embeddings[:, i]
        
    # Centrality and bottleneck metrics
    node_metrics_map = metrics.set_index('hub_id')[['betweenness', 'bottleneck_score', 'avg_outgoing_delay', 'clustering', 'pagerank']].to_dict('index')
    
    def get_node_metric(node_id, metric_name):
        return node_metrics_map.get(node_id, {}).get(metric_name, 0.0)

    for metric in ['betweenness', 'bottleneck_score', 'avg_outgoing_delay', 'clustering', 'pagerank']:
        df_trip[f'src_{metric}'] = df_trip['source_center'].apply(lambda x: get_node_metric(x, metric))
        df_trip[f'dst_{metric}'] = df_trip['destination_center'].apply(lambda x: get_node_metric(x, metric))

    # 3. Features: Baseline + Graph features
    baseline_features = [
        'osrm_time', 'osrm_distance', 'n_segments', 'trip_hour', 
        'trip_dayofweek', 'trip_month', 'is_weekend', 'pct_delayed_segs'
    ]
    graph_features = [f'src_n2v_{i}' for i in range(32)] + [f'dst_n2v_{i}' for i in range(32)] + \
                     [f'src_{m}' for m in ['betweenness', 'bottleneck_score', 'avg_outgoing_delay', 'clustering', 'pagerank']] + \
                     [f'dst_{m}' for m in ['betweenness', 'bottleneck_score', 'avg_outgoing_delay', 'clustering', 'pagerank']]
    
    features = baseline_features + graph_features
    
    X = df_trip[features].copy()
    route_dummies = pd.get_dummies(df_trip['route_type'], prefix='route')
    X = pd.concat([X, route_dummies], axis=1)
    
    y = df_trip['actual_time']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=df_trip['route_type'], random_state=RANDOM_STATE
    )
    
    model = xgb.XGBRegressor(
        n_estimators=300, 
        learning_rate=0.05,
        max_depth=6, 
        subsample=0.8, 
        colsample_bytree=0.8,
        random_state=RANDOM_STATE
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    # Evaluation
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mask = y_test != 0
    accuracy_15pct = np.mean(np.abs((y_test[mask] - y_pred[mask]) / y_test[mask]) <= 0.15)
    
    print(f"Graph-Enhanced Results: MAE={mae:.2f}, RMSE={rmse:.2f}, Within 15% Accuracy={accuracy_15pct:.2%}")
    
    # Save embeddings for inference
    os.makedirs('outputs/models', exist_ok=True)
    embeddings_map = {node: get_embedding(node) for node in G.nodes()}
    joblib.dump(embeddings_map, 'outputs/models/node_embeddings.joblib')

    return {
        'model': model,
        'predictions': y_pred,
        'metrics': {'mae': mae, 'rmse': rmse, 'within_15pct': accuracy_15pct},
        'X_test': X_test,
        'y_test': y_test,
        'test_indices': X_test.index
    }

def predict_eta(model, features_df: pd.DataFrame) -> np.ndarray:
    """
    Predict ETA using a trained model.
    """
    return model.predict(features_df)

def benchmark(baseline_results: Dict, graph_results: Dict) -> pd.DataFrame:
    """
    Compare baseline vs graph-enhanced models.

    Args:
        baseline_results: Dict from train_baseline
        graph_results: Dict from train_graph_model

    Returns:
        DataFrame with comparison table
    """
    b_met = baseline_results['metrics']
    g_met = graph_results['metrics']
    
    comparison = pd.DataFrame({
        'Model': ['Baseline', 'Graph-Enhanced', 'Improvement'],
        'MAE (min)': [b_met['mae'], g_met['mae'], g_met['mae'] - b_met['mae']],
        'RMSE (min)': [b_met['rmse'], g_met['rmse'], g_met['rmse'] - b_met['rmse']],
        'Within 15% accuracy': [f"{b_met['within_15pct']:.2%}", f"{g_met['within_15pct']:.2%}", f"{(g_met['within_15pct'] - b_met['within_15pct'])*100:+.2f} pp"]
    })
    
    print("\nModel Benchmark Comparison:")
    print(comparison.to_string(index=False))
    
    os.makedirs('outputs/reports', exist_ok=True)
    with open('outputs/reports/model_benchmark.txt', 'w') as f:
        f.write(comparison.to_string(index=False))
        
    return comparison

def save_models(baseline_results: Dict, graph_results: Dict, output_dir: str):
    """
    Save trained models.
    """
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(baseline_results['model'], os.path.join(output_dir, 'baseline_eta_model.joblib'))
    joblib.dump(graph_results['model'], os.path.join(output_dir, 'graph_enhanced_eta_model.joblib'))
    print(f"Models saved to {output_dir}")
