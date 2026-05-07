# Delhivery Graph Intelligence System

A production-ready Graph-Based Network Intelligence System built for Delhivery's logistics network. This system models the entire logistics infrastructure as a directed weighted graph to improve ETA predictions, identify hub bottlenecks, and provide data-backed operational recommendations.

## 🚀 Key Features

*   **Graph-Enhanced ETA:** Outperforms standard OSRM baselines by using Node2Vec structural embeddings and hub centrality metrics (+10.7 pp improvement in accuracy).
*   **Bottleneck Detection:** Identifies critical chokepoints using a composite **Bottleneck Priority Score** (Betweenness, PageRank, and Congestion).
*   **Route Optimizer:** ML-backed framework recommending **FTL vs. Carting** shifts based on corridor stability and hub traffic.
*   **Interactive Dashboard:** 5-page Streamlit application with live model inference, interactive network maps, and real-time corridor filtering.
*   **Financial Impact Analysis:** Quantifies "Revenue at Risk" (INR) and estimates the recovery potential of facility upgrades.

## 🛠️ Tech Stack

*   **Graph Processing:** NetworkX, Node2Vec
*   **Machine Learning:** XGBoost, Scikit-Learn
*   **Data Engineering:** Pandas, NumPy, SciPy
*   **Visualization:** Plotly, Seaborn, Matplotlib
*   **Dashboard:** Streamlit

## 📁 Project Structure

```text
delhivery_graph_intelligence/
├── data/                  # Place delivery_data.csv here
├── outputs/               # Generated figures, models, and CSV reports
├── src/
│   ├── pipeline.py        # Data cleaning & aggregation
│   ├── graph_builder.py   # NetworkX graph construction
│   ├── graph_metrics.py   # Centrality & Bottleneck scoring
│   ├── eta_model.py       # XGBoost ETA prediction models
│   ├── route_classifier.py# FTL vs Carting recommendation
│   └── visualise.py       # Static & Interactive plotting
├── app.py                 # Streamlit Dashboard
├── run_all.py             # Master execution script
└── strategy_memo.md       # Auto-generated executive report
```

## 🏃 How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the Analysis Pipeline:**
    ```bash
    python run_all.py
    ```
3.  **Launch the Dashboard:**
    ```bash
    streamlit run app.py
    ```

## 📊 Business Impact

The system identified **2,617 chronic delay corridors**. By upgrading the top 3 identified bottleneck hubs to network median efficiency, Delhivery can potentially recover **₹1.05 Crore** in revenue currently lost to SLA breach penalties.

---
*Developed as part of the Graph Intelligence Build for Delhivery Operations.*
