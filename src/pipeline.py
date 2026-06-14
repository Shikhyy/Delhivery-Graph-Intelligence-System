import pandas as pd
import numpy as np
import re
from scipy import stats
from typing import Dict, Tuple

def load_and_clean(path: str) -> pd.DataFrame:
    """
    Load CSV, clean data, extract features, and handle outliers.

    Args:
        path: Path to delivery_data.csv

    Returns:
        Cleaned pandas DataFrame
    """
    print(f"Loading data from {path}...")
    df = pd.read_csv(path)
    initial_shape = df.shape
    print(f"Initial shape: {initial_shape}")

    # Drop unnecessary columns
    cols_to_drop = ['is_cutoff', 'cutoff_factor', 'cutoff_timestamp', 'factor', 'segment_factor']
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # Parse datetime columns
    date_cols = ['trip_creation_time', 'od_start_time', 'od_end_time']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col])

    # Convert categorical columns
    categorical_cols = ['route_type', 'data']
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')

    # Extract city and state from source/destination names
    # Format: "CityName Place (ST)"
    def extract_loc(name: str):
        if pd.isna(name):
            return None, None
        match = re.search(r'^(.*?)\s+.*?\((.*?)\)$', str(name))
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return str(name), None

    print("Extracting location features...")
    df['src_city'], df['src_state'] = zip(*df['source_name'].apply(extract_loc))
    df['dst_city'], df['dst_state'] = zip(*df['destination_name'].apply(extract_loc))

    # Temporal features
    print("Extracting temporal features...")
    df['trip_hour'] = df['trip_creation_time'].dt.hour
    df['trip_dayofweek'] = df['trip_creation_time'].dt.dayofweek
    df['trip_month'] = df['trip_creation_time'].dt.month
    df['is_weekend'] = df['trip_dayofweek'].isin([5, 6])

    def get_time_of_day(hour):
        if 0 <= hour < 6: return 'late_night'
        elif 6 <= hour < 12: return 'morning'
        elif 12 <= hour < 18: return 'afternoon'
        else: return 'evening'

    df['time_of_day'] = df['trip_hour'].apply(get_time_of_day).astype('category')

    # Delay metrics
    df['delay_ratio'] = (df['segment_actual_time'] / df['segment_osrm_time']).clip(0.01, 10.0)
    df['trip_delay_ratio'] = (df['actual_time'] / df['osrm_time']).clip(0.01, 10.0)
    df['is_delayed'] = (df['delay_ratio'] > 1.20).astype(int)

    # Winsorization at 1st and 99th percentiles
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    print("Applying winsorization...")
    for col in numeric_cols:
        if col not in ['source_center', 'destination_center', 'is_delayed', 'trip_hour', 'trip_dayofweek', 'trip_month']:
            lower = df[col].quantile(0.01)
            upper = df[col].quantile(0.99)
            df[col] = df[col].clip(lower, upper)

    # Drop rows with critical nulls
    critical_cols = ['segment_actual_time', 'segment_osrm_time', 'source_center', 'destination_center']
    df = df.dropna(subset=critical_cols)

    print(f"Final shape after cleaning: {df.shape}")
    return df

def aggregate_to_trips(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate segment-level data to trip-level.

    Args:
        df: Cleaned segment-level DataFrame

    Returns:
        Trip-level DataFrame
    """
    print("Aggregating segments to trips...")
    
    # Define aggregation logic
    agg_dict = {
        'route_type': 'first',
        'source_center': 'first',
        'destination_center': 'first',
        'src_city': 'first',
        'src_state': 'first',
        'dst_city': 'first',
        'dst_state': 'first',
        'trip_hour': 'first',
        'trip_dayofweek': 'first',
        'trip_month': 'first',
        'is_weekend': 'first',
        'time_of_day': 'first',
        'actual_time': 'first',
        'osrm_time': 'first',
        'actual_distance_to_destination': 'first',
        'osrm_distance': 'first',
        'segment_actual_time': 'sum',
        'segment_osrm_time': 'sum',
        'segment_osrm_distance': 'sum',
        'delay_ratio': ['mean', 'max'],
        'is_delayed': 'sum'
    }

    df_trip = df.groupby('trip_uuid').agg(agg_dict)
    
    # Flatten columns
    df_trip.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df_trip.columns]
    
    # Rename flattened columns for clarity
    df_trip = df_trip.rename(columns={
        'route_type_first': 'route_type',
        'source_center_first': 'source_center',
        'destination_center_first': 'destination_center',
        'src_city_first': 'src_city',
        'src_state_first': 'src_state',
        'dst_city_first': 'dst_city',
        'dst_state_first': 'dst_state',
        'trip_hour_first': 'trip_hour',
        'trip_dayofweek_first': 'trip_dayofweek',
        'trip_month_first': 'trip_month',
        'is_weekend_first': 'is_weekend',
        'time_of_day_first': 'time_of_day',
        'actual_time_first': 'actual_time',
        'osrm_time_first': 'osrm_time',
        'actual_distance_to_destination_first': 'actual_distance_to_destination',
        'osrm_distance_first': 'osrm_distance',
        'segment_actual_time_sum': 'seg_actual_sum',
        'segment_osrm_time_sum': 'seg_osrm_sum',
        'segment_osrm_distance_sum': 'seg_dist_sum',
        'delay_ratio_mean': 'delay_ratio_mean',
        'delay_ratio_max': 'delay_ratio_max',
        'is_delayed_sum': 'n_delayed_segs'
    })

    # Count segments per trip
    df_trip['n_segments'] = df.groupby('trip_uuid').size()
    
    # Derived metrics
    df_trip['pct_delayed_segs'] = df_trip['n_delayed_segs'] / df_trip['n_segments']
    df_trip['trip_is_sla_breach'] = (df_trip['delay_ratio_mean'] > 1.20)

    print(f"Total trips: {len(df_trip)}")
    print(f"SLA Breach Rate: {df_trip['trip_is_sla_breach'].mean():.2%}")

    return df_trip

def run_hypothesis_tests(df: pd.DataFrame) -> Dict:
    """
    Run Mann-Whitney U tests for key distributions.

    Args:
        df: Cleaned segment-level DataFrame (or trip-level where applicable)

    Returns:
        Dictionary of p-values and interpretations
    """
    print("Running hypothesis tests...")
    results = {}

    # Need trip-level for some tests
    df_trip = aggregate_to_trips(df)

    # 1. actual_time vs seg_actual_sum
    stat, p = stats.mannwhitneyu(df_trip['actual_time'], df_trip['seg_actual_sum'])
    results['actual_vs_seg_sum'] = {'p_value': p, 'interpretation': "Significant difference" if p < 0.05 else "No significant difference"}

    # 2. osrm_time vs seg_osrm_sum
    stat, p = stats.mannwhitneyu(df_trip['osrm_time'], df_trip['seg_osrm_sum'])
    results['osrm_vs_seg_sum'] = {'p_value': p, 'interpretation': "Significant difference" if p < 0.05 else "No significant difference"}

    # 3. delay_ratio for FTL vs Carting
    ftl_delay = df[df['route_type'] == 'FTL']['delay_ratio']
    carting_delay = df[df['route_type'] == 'Carting']['delay_ratio']
    stat, p = stats.mannwhitneyu(ftl_delay, carting_delay)
    results['ftl_vs_carting_delay'] = {'p_value': p, 'interpretation': "Route type affects delay" if p < 0.05 else "No significant difference"}

    # 4. delay_ratio by time_of_day (using Kruskal-Wallis for >2 groups)
    groups = [group['delay_ratio'].values for name, group in df.groupby('time_of_day', observed=True)]
    stat, p = stats.kruskal(*groups)
    results['time_of_day_delay'] = {'p_value': p, 'interpretation': "Time of day affects delay" if p < 0.05 else "No significant difference"}

    for test, res in results.items():
        print(f"Test {test}: p={res['p_value']:.4f} -> {res['interpretation']}")

    return results
