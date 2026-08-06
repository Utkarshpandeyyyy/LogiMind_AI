
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import networkx as nx
import json

import importlib
import engine
import order_agent
importlib.reload(engine)
importlib.reload(order_agent)
from engine import simulate, risk_level, answer_copilot

BASE_DIR = Path(__file__).parent

st.set_page_config(
    page_title="LogiMind AI",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 2rem;}
.hero {
    padding: 1.2rem 1.4rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: white;
    margin-bottom: 1rem;
}
.hero h1 {margin: 0; font-size: 2.1rem;}
.hero p {margin: .35rem 0 0; color: #cbd5e1;}
.card {
    padding: 1rem;
    border: 1px solid rgba(128,128,128,.2);
    border-radius: 14px;
}
.small {font-size: .88rem; opacity: .8;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    shipments = pd.read_csv(BASE_DIR / "data" / "shipments.csv")
    warehouses = pd.read_csv(BASE_DIR / "data" / "warehouses.csv")
    return shipments, warehouses

shipments, warehouses = load_data()
# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

# Credentials
USER_ROLES = {
    "Executive (Admin)": "admin123",
    "Logistics Operator": "ops123",
    "Guest (Viewer)": "guest123"
}

if not st.session_state["logged_in"]:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 2rem; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 2rem;">
            <h2 style="color: white; margin-top: 0;">🔒 Secure Logistics Access Control</h2>
            <p style="color: #94a3b8; font-size: 0.95rem;">Please select your corporate credentials to access the LogiMind AI Platform.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    with st.form("login_form"):
        role = st.selectbox("Select User Role", list(USER_ROLES.keys()))
        password = st.text_input("Enter Access Password", type="password", placeholder="••••••••")
        submit = st.form_submit_button("Authenticate Access", use_container_width=True)
        
        if submit:
            expected_pass = USER_ROLES.get(role)
            if password == expected_pass:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = role
                st.success(f"Successfully authenticated as {role}!")
                st.rerun()
            else:
                st.error("Incorrect password for the selected role. Please try again.")
                
    st.stop()

# If logged in, filter navigation based on role permissions
role = st.session_state["user_role"]

# Define authorized views
if role == "Executive (Admin)":
    allowed_pages = ["Executive Control Tower", "Digital Twin Simulator", "Network Intelligence", "AI Copilot", "Data Governance & MDM"]
elif role == "Logistics Operator":
    allowed_pages = ["Digital Twin Simulator", "Network Intelligence", "AI Copilot"]
else:  # Guest (Viewer)
    allowed_pages = ["Executive Control Tower", "Network Intelligence"]

# Sidebar authentication panel
st.sidebar.markdown(f"**Authenticated**: `{role}`")
if st.sidebar.button("Log Out Session", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.rerun()

st.sidebar.divider()

st.sidebar.title("LogiMind AI")
st.sidebar.caption("Autonomous Supply Chain Decision Intelligence")
page = st.sidebar.radio("Navigate", allowed_pages)

st.sidebar.divider()
st.sidebar.info(
    "Demo mode uses simulated enterprise logistics data. "
    "Production integrations can connect ERP, WMS, GPS, weather and fleet systems."
)

st.markdown(
    """
    <div class="hero">
      <h1>LogiMind AI</h1>
      <p>Predict disruption. Simulate alternatives. Recommend the best business action.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "Executive Control Tower":
    total = len(shipments)
    delayed = int((shipments.status == "Delayed").sum())
    critical = int((shipments.risk_score >= 70).sum())
    exposure = int(shipments.loc[shipments.risk_score >= 60, "shipment_value_inr"].sum())
    sla = int(max(0, 100 - shipments.predicted_delay_hours.mean() * 4.5))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Shipments", total)
    c2.metric("Delayed", delayed)
    c3.metric("Critical Risk", critical)
    c4.metric("Value at Risk", f"₹{exposure/1e6:.1f}M")
    c5.metric("Network SLA", f"{sla}%")

    left, right = st.columns([1.15, 1])

    with left:
        st.subheader("Live Shipment Network")
        fig = go.Figure()
        for _, row in shipments.head(35).iterrows():
            fig.add_trace(go.Scattermapbox(
                mode="lines",
                lon=[row.origin_lon, row.destination_lon],
                lat=[row.origin_lat, row.destination_lat],
                line={"width": 1.5},
                opacity=0.45,
                hoverinfo="text",
                text=f"{row.shipment_id}: {row.origin} → {row.destination} | Risk {row.risk_score}",
                showlegend=False,
            ))
        city_df = pd.DataFrame([
            {"city": c, "lat": lat, "lon": lon} 
            for c, (lat, lon) in {
                "Delhi": (28.6139, 77.2090),
                "Mumbai": (19.0760, 72.8777),
                "Bengaluru": (12.9716, 77.5946),
                "Chennai": (13.0827, 80.2707),
                "Hyderabad": (17.3850, 78.4867),
                "Kolkata": (22.5726, 88.3639),
            }.items()
        ])
        fig.add_trace(go.Scattermapbox(
            lat=city_df.lat, lon=city_df.lon, mode="markers+text",
            text=city_df.city, textposition="top right",
            marker={"size": 11}, showlegend=False
        ))
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox={"center": {"lat": 21.3, "lon": 79.0}, "zoom": 3.4},
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            height=430,
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Risk Distribution")
        risk_counts = shipments.assign(
            risk_band=shipments.risk_score.apply(risk_level)
        ).groupby("risk_band").size().reset_index(name="count")
        order = ["Low", "Medium", "High", "Critical"]
        risk_counts["risk_band"] = pd.Categorical(risk_counts["risk_band"], order)
        risk_counts = risk_counts.sort_values("risk_band")
        fig = px.bar(risk_counts, x="risk_band", y="count", text="count")
        fig.update_layout(height=270, xaxis_title="", yaxis_title="Shipments")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Warehouse Pressure")
        fig = px.bar(
            warehouses.sort_values("capacity_pct"),
            x="capacity_pct", y="warehouse", orientation="h",
            text="capacity_pct",
        )
        fig.update_layout(height=265, xaxis_title="Capacity %", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("AI Action Queue")
    action_df = shipments.sort_values("risk_score", ascending=False).head(10).copy()
    action_df["recommended_action"] = action_df.apply(
        lambda r: (
            "Reroute + backup vehicle" if r.traffic in ["High", "Severe"]
            else "Shift warehouse" if r.warehouse_load == "Overloaded"
            else "Advance dispatch" if r.weather in ["Heavy Rain", "Storm"]
            else "Monitor"
        ), axis=1
    )
    st.dataframe(
        action_df[[
            "shipment_id", "origin", "destination", "priority", "risk_score",
            "predicted_delay_hours", "shipment_value_inr", "recommended_action"
        ]],
        use_container_width=True,
        hide_index=True,
    )

elif page == "Digital Twin Simulator":
    st.subheader("What-if Scenario Engine")
    st.caption("Change operating conditions and compare the network outcome before acting.")

    c1, c2, c3 = st.columns(3)
    with c1:
        distance = st.slider("Route distance (km)", 100, 2500, 850, 50)
        weather = st.selectbox("Weather", ["Clear", "Rain", "Heavy Rain", "Storm"])
        traffic = st.selectbox("Traffic", ["Low", "Medium", "High", "Severe"])
    with c2:
        vehicle = st.selectbox("Vehicle health", ["Good", "Average", "Poor"])
        warehouse = st.selectbox("Warehouse load", ["Normal", "Busy", "Overloaded"])
        priority = st.selectbox("Shipment priority", ["Standard", "High", "Critical"])
    with c3:
        warehouse_closed = st.toggle("Warehouse closed")
        fuel = st.slider("Fuel price increase (%)", 0, 30, 0)

    baseline = simulate(distance, "Clear", "Low", "Good", "Normal", priority, False, 0)
    scenario = simulate(distance, weather, traffic, vehicle, warehouse, priority, warehouse_closed, fuel)

    st.divider()
    a, b, c, d, e = st.columns(5)
    a.metric("Predicted Delay", f"{scenario.delay_hours} h", f"{scenario.delay_hours-baseline.delay_hours:+.1f} h")
    b.metric("Risk Score", f"{scenario.risk_score}/100")
    c.metric("SLA Probability", f"{scenario.sla_probability_pct}%")
    d.metric("Estimated Cost", f"₹{scenario.estimated_cost_inr:,.0f}")
    e.metric("Carbon", f"{scenario.carbon_kg:,.0f} kg")

    st.success(f"Recommended action: {scenario.recommended_action}")
    st.info(scenario.explanation)

    comparison = pd.DataFrame({
        "Metric": ["Delay hours", "Risk score", "Cost (₹000)", "Carbon (kg/10)", "SLA probability"],
        "Baseline": [
            baseline.delay_hours, baseline.risk_score, baseline.estimated_cost_inr / 1000,
            baseline.carbon_kg / 10, baseline.sla_probability_pct
        ],
        "Scenario": [
            scenario.delay_hours, scenario.risk_score, scenario.estimated_cost_inr / 1000,
            scenario.carbon_kg / 10, scenario.sla_probability_pct
        ],
    })
    fig = px.bar(
        comparison.melt("Metric", var_name="Case", value_name="Value"),
        x="Metric", y="Value", color="Case", barmode="group",
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "Network Intelligence":
    st.subheader("Supply Chain Relationship Graph")
    st.caption("Shows how suppliers, warehouses, routes and customers are connected.")

    G = nx.Graph()
    suppliers = ["Supplier North", "Supplier West", "Supplier South"]
    hubs = ["Delhi Hub", "Mumbai Hub", "Bengaluru Hub", "Chennai Hub"]
    customers = ["Retail A", "Retail B", "Enterprise C", "Premium D"]

    for s in suppliers:
        G.add_node(s, type="Supplier")
    for h in hubs:
        G.add_node(h, type="Warehouse")
    for c in customers:
        G.add_node(c, type="Customer")

    edges = [
        ("Supplier North", "Delhi Hub"), ("Supplier West", "Mumbai Hub"),
        ("Supplier South", "Bengaluru Hub"), ("Supplier South", "Chennai Hub"),
        ("Delhi Hub", "Retail A"), ("Delhi Hub", "Enterprise C"),
        ("Mumbai Hub", "Retail B"), ("Bengaluru Hub", "Premium D"),
        ("Chennai Hub", "Retail A"), ("Mumbai Hub", "Premium D"),
    ]
    G.add_edges_from(edges)

    pos = nx.spring_layout(G, seed=7)
    edge_x, edge_y = [], []
    for a, b in G.edges():
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="none")
    node_x, node_y, labels, node_types = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); labels.append(node)
        node_types.append(G.nodes[node]["type"])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=labels,
        textposition="top center",
        hovertext=node_types, hoverinfo="text",
        marker={"size": 24},
    )
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(height=520, showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                      xaxis={"visible": False}, yaxis={"visible": False})
    st.plotly_chart(fig, use_container_width=True)

    disrupted = st.selectbox("Simulate node failure", ["None"] + hubs)
    if disrupted != "None":
        affected = list(G.neighbors(disrupted))
        st.error(f"{disrupted} failure directly impacts: {', '.join(affected)}")
        st.warning("AI response: reassign orders to the nearest healthy hub and protect premium-customer SLAs first.")

elif page == "AI Copilot":
    st.subheader("Executive Supply Chain Copilot")
    st.caption("Ask business questions in plain English.")

    examples = [
        "Which shipment has the highest risk?",
        "What happens if the Chennai warehouse closes?",
        "How many shipments are delayed?",
        "Which warehouse is at risk?",
        "Where can we save cost?",
    ]
    selected = st.selectbox("Example questions", ["Type my own question"] + examples)
    default_q = "" if selected == "Type my own question" else selected
    question = st.text_input("Ask LogiMind AI", value=default_q, placeholder="e.g. What happens if Chennai closes?")

    if st.button("Analyse", type="primary", use_container_width=True):
        if question.strip():
            answer = answer_copilot(question, shipments, warehouses)
            st.markdown("### AI Response")
            st.write(answer)

            high = shipments.sort_values("risk_score", ascending=False).head(5)
            st.markdown("#### Evidence")
            st.dataframe(
                high[["shipment_id", "origin", "destination", "risk_score", "predicted_delay_hours", "status"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("Enter a question first.")

elif page == "Data Governance & MDM":
    st.subheader("Medallion Data Pipeline & Master Data Management")
    st.caption("Visualizing Kafka ingestion, Medallion processing (Bronze/Silver/Gold), and SSH infrastructure tools.")
    
    import data_pipeline
    
    # 1. Pipeline Execution Control
    col1, col2 = st.columns([1, 1.25])
    with col1:
        st.markdown("### Pipeline Execution")
        st.info("Trigger a mock cycle of the data pipeline. This simulates Kafka event streaming, cleans raw logs, and regenerates Gold analytical metrics.")
        if st.button("Run Ingestion Pipeline", type="primary", use_container_width=True):
            with st.spinner("Processing pipeline layers (Bronze → Silver → Gold)..."):
                kpi_data = data_pipeline.execute_full_pipeline()
                if kpi_data:
                    st.success("Pipeline executed successfully!")
                else:
                    st.error("Pipeline run failed.")
                    
        # Display folder stats
        bronze_count = len(list(data_pipeline.BRONZE_DIR.glob("*.json"))) if data_pipeline.BRONZE_DIR.exists() else 0
        silver_count = len(list(data_pipeline.SILVER_DIR.glob("*.csv"))) if data_pipeline.SILVER_DIR.exists() else 0
        gold_exists = (data_pipeline.GOLD_DIR / "kpi_dashboard.json").exists()
        
        st.markdown("#### Data Lake Inventory")
        st.markdown(f"- 📁 **Bronze Zone (Raw JSON)**: `{bronze_count}` file(s)")
        st.markdown(f"- 📁 **Silver Zone (Clean CSV)**: `{silver_count}` file(s)")
        st.markdown(f"- 📁 **Gold Zone (KPI Metrics)**: `{'1' if gold_exists else '0'}` file(s)")
        
    with col2:
        st.markdown("### Medallion Pipeline Architecture")
        # Visual diagram of the architecture using HTML/CSS
        st.markdown("""
        <div style="background: rgba(128,128,128,0.1); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2);">
          <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
            <div style="flex: 1; padding: 0.5rem; background: #3b2314; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #d97706;">Bronze Zone</strong><br/>
              <span style="font-size: 0.8rem; color: #f59e0b;">Raw Ingestion</span>
            </div>
            <div style="color: #cbd5e1;">➔</div>
            <div style="flex: 1; padding: 0.5rem; background: #1e293b; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #94a3b8;">Silver Zone</strong><br/>
              <span style="font-size: 0.8rem; color: #cbd5e1;">Cleaned & Valid</span>
            </div>
            <div style="color: #cbd5e1;">➔</div>
            <div style="flex: 1; padding: 0.5rem; background: #133b1e; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #16a34a;">Gold Zone</strong><br/>
              <span style="font-size: 0.8rem; color: #4ade80;">Aggregated KPIs</span>
            </div>
          </div>
          <div style="margin-top: 1rem; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">
            <strong>Mock Kafka Broker</strong> status: <code>Running (Simulated)</code><br/>
            <strong>Ingestion Source</strong>: Streaming device logs mock (<code>shipments.csv</code>)<br/>
            <strong>Storage Format</strong>: Structured Local directories (S3-compatible folder mock)
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display preview of Gold KPI if exists
        gold_path = data_pipeline.GOLD_DIR / "kpi_dashboard.json"
        if gold_path.exists():
            st.markdown("#### Latest Gold Dashboard KPIs")
            with open(gold_path, "r") as f:
                kpi_data = json.load(f)
            st.json(kpi_data)
            
    st.divider()
    
    # 2. SSH Infrastructure reference console
    st.markdown("### SSH & Operations Console Reference")
    st.info("Below are the exact security and operations console commands remote into production nodes, configure keys, and tunnel ports.")
    
    ssh_left, ssh_right = st.columns(2)
    with ssh_left:
        st.markdown("#### SSH Command Guide")
        st.code("""
# 1. Generate SSH Key pair (Ed25519)
ssh-keygen -t ed25519 -b 4096 -C "admin@logimind.ai"

# 2. Copy Public Key to remote host
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@192.168.1.100

# 3. Securely connect to your remote node
ssh -i ~/.ssh/id_ed25519 root@192.168.1.100

# 4. Check running Docker containers on server
ssh root@192.168.1.100 "docker ps"
        """, language="bash")
        
    with ssh_right:
        st.markdown("#### Kafka Tunneling & SCP Guide")
        st.code("""
# 1. Forward remote Kafka broker (9092) and UI (8080) to localhost
ssh -L 9092:localhost:9092 -L 8080:localhost:8080 root@192.168.1.100 -N

# 2. Verify local connectivity to forwarded Kafka
kafkacat -b localhost:9092 -L

# 3. SCP: Send file to remote server Data Lake
scp ./data/shipments.csv root@192.168.1.100:/opt/datalake/bronze/

# 4. SCP: Backup gold report from remote to local
scp root@192.168.1.100:/opt/datalake/gold/kpi_dashboard.json ./backups/
        """, language="bash")
