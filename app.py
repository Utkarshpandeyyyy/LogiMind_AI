from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import networkx as nx
import json
try:
    import psycopg2
except ImportError:
    psycopg2 = None

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
    if psycopg2 is None:
        shipments = pd.read_csv(BASE_DIR / "data" / "shipments.csv")
        warehouses = pd.read_csv(BASE_DIR / "data" / "warehouses.csv")
        return shipments, warehouses, False
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            dbname="logimind"
        )
        shipments = pd.read_sql_query("SELECT * FROM shipments;", conn)
        warehouses = pd.read_sql_query("SELECT * FROM warehouses;", conn)
        conn.close()
        return shipments, warehouses, True
    except Exception as e:
        shipments = pd.read_csv(BASE_DIR / "data" / "shipments.csv")
        warehouses = pd.read_csv(BASE_DIR / "data" / "warehouses.csv")
        return shipments, warehouses, False

shipments, warehouses, is_live_db = load_data()

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "tour_step" not in st.session_state:
    st.session_state["tour_step"] = "Welcome (Manual Navigation)"
if "login_count" not in st.session_state:
    st.session_state["login_count"] = 0

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
                st.session_state["login_count"] += 1
                
                # First login defaults to starting the tour, subsequent logins default to manual navigation (hiding the tour guide)
                if st.session_state["login_count"] == 1:
                    st.session_state["tour_step"] = "Stop 1: Executive Control Tower"
                else:
                    st.session_state["tour_step"] = "Welcome (Manual Navigation)"
                    
                st.success(f"Successfully authenticated as {role}!")
                st.rerun()
            else:
                st.error("Incorrect password for the selected role. Please try again.")
        # Future RBAC authentication options (Roadmap Placeholder)
    st.write("")
    st.markdown("### 🗺️ Future Authentication Roadmap (Planned Features)")
    c_sso, c_bio, c_req = st.columns(3)
    if c_sso.button("🔒 Sign In with SSO / SAML", use_container_width=True):
        st.toast("🚧 SSO Integration is planned for Enterprise release v2.0.")
    if c_bio.button("🤖 Sign In with Biometrics / FaceID", use_container_width=True):
        st.toast("🚧 Biometrics/FaceID login will be supported on mobile apps in Q4.")
    if c_req.button("✉️ Request Access / Sign Up", use_container_width=True):
        st.toast("🚧 Self-registration requests will be routed to IT administrators in Q3.")
        
    st.stop()

# If logged in, filter navigation based on role permissions
role = st.session_state["user_role"]

# Define authorized views
if role == "Executive (Admin)":
    allowed_pages = ["Executive Control Tower", "Digital Twin Simulator", "Network Intelligence", "AI Copilot", "Data Governance & MDM"]
elif role == "Logistics Operator":
    allowed_pages = ["Executive Control Tower", "Digital Twin Simulator", "Network Intelligence", "AI Copilot"]
else:  # Guest (Viewer)
    allowed_pages = ["Executive Control Tower", "Network Intelligence"]

# Sidebar authentication panel
st.sidebar.markdown(f"**Authenticated**: `{role}`")
if is_live_db:
    st.sidebar.success("📡 DB Mode: Live (PostgreSQL)")
else:
    st.sidebar.warning("⚠️ DB Mode: Fallback (Static CSV)")

if st.sidebar.button("Log Out Session", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.rerun()

st.sidebar.divider()

# Guided Platform Tour Selector
st.sidebar.subheader("🧭 Guided Platform Tour")
tour_stops = ["Welcome (Manual Navigation)"]
if "Executive Control Tower" in allowed_pages:
    tour_stops.append("Stop 1: Executive Control Tower")
if "Digital Twin Simulator" in allowed_pages:
    tour_stops.append("Stop 2: What-if Digital Twin")
if "Network Intelligence" in allowed_pages:
    tour_stops.append("Stop 3: Network Graph Resiliency")
if "AI Copilot" in allowed_pages:
    tour_stops.append("Stop 4: Conversational AI Copilot")
if "Data Governance & MDM" in allowed_pages:
    tour_stops.append("Stop 5: Data Operations & Cleaning")

# Set active page in session state if not existing
if "active_page" not in st.session_state:
    st.session_state["active_page"] = allowed_pages[0]

# Determine selected index for selectbox
current_tour_index = 0
if st.session_state["tour_step"] in tour_stops:
    current_tour_index = tour_stops.index(st.session_state["tour_step"])

selected_tour_stop = st.sidebar.selectbox("Current Tour Stop", tour_stops, index=current_tour_index)

# Force page navigation depending on tour selection
if selected_tour_stop != "Welcome (Manual Navigation)":
    st.session_state["tour_step"] = selected_tour_stop
    if selected_tour_stop == "Stop 1: Executive Control Tower" and "Executive Control Tower" in allowed_pages:
        st.session_state["active_page"] = "Executive Control Tower"
    elif selected_tour_stop == "Stop 2: What-if Digital Twin" and "Digital Twin Simulator" in allowed_pages:
        st.session_state["active_page"] = "Digital Twin Simulator"
    elif selected_tour_stop == "Stop 3: Network Graph Resiliency" and "Network Intelligence" in allowed_pages:
        st.session_state["active_page"] = "Network Intelligence"
    elif selected_tour_stop == "Stop 4: Conversational AI Copilot" and "AI Copilot" in allowed_pages:
        st.session_state["active_page"] = "AI Copilot"
    elif selected_tour_stop == "Stop 5: Data Operations & Cleaning" and "Data Governance & MDM" in allowed_pages:
        st.session_state["active_page"] = "Data Governance & MDM"
else:
    if st.session_state["tour_step"] != "Welcome (Manual Navigation)":
        st.session_state["tour_step"] = "Welcome (Manual Navigation)"

# Standard page selector
# Use active_page from session state as default value
default_nav_index = 0
if "active_page" in st.session_state and st.session_state["active_page"] in allowed_pages:
    default_nav_index = allowed_pages.index(st.session_state["active_page"])

page = st.sidebar.radio("Navigate", allowed_pages, index=default_nav_index)
st.session_state["active_page"] = page

# Bidirectional sync: Update selectbox if user navigates manually
if page == "Executive Control Tower":
    st.session_state["tour_step"] = "Stop 1: Executive Control Tower"
elif page == "Digital Twin Simulator":
    st.session_state["tour_step"] = "Stop 2: What-if Digital Twin"
elif page == "Network Intelligence":
    st.session_state["tour_step"] = "Stop 3: Network Graph Resiliency"
elif page == "AI Copilot":
    st.session_state["tour_step"] = "Stop 4: Conversational AI Copilot"
elif page == "Data Governance & MDM":
    st.session_state["tour_step"] = "Stop 5: Data Operations & Cleaning"
# Future Roadmap: Real-Time GPS Tracker Status
st.sidebar.divider()
st.sidebar.subheader("📡 Live GPS Stream (Roadmap)")
mock_trackers = [
    "Select Active Truck...", 
    "Truck DL-10-A (Delhi Corridors)", 
    "Truck MH-02-B (Mumbai Port)", 
    "Truck KA-51-C (Bengaluru Depot)",
    "Truck TN-09-D (Chennai Hub)"
]
selected_mock_tracker = st.sidebar.selectbox(
    "Live Vehicle Feed (Future Work)", 
    mock_trackers,
    help="Planned integration for real-time telemetry streaming."
)
if selected_mock_tracker != "Select Active Truck...":
    st.sidebar.info(f"🚧 **Future Work**: Live telemetry stream for **{selected_mock_tracker.split(' ')[1]}** is under development. Real-time path tracing is planned for release v2.1.")

st.sidebar.divider()
st.sidebar.title("LogiMind AI")
st.sidebar.caption("Autonomous Supply Chain Decision Intelligence")

st.markdown(
    """
    <div class="hero">
      <h1>LogiMind AI</h1>
      <p>Predict disruption. Simulate alternatives. Recommend the best business action.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Display active Tour Guide Banner
if st.session_state["tour_step"] != "Welcome (Manual Navigation)":
    if page == "Executive Control Tower":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a, #0d9488); padding: 1.2rem; border-radius: 14px; border-left: 6px solid #38bdf8; margin-bottom: 1.2rem; color: white;">
          <h4 style="margin: 0; color: white; font-size: 1.15rem;">🧭 Tour Guide • Stop 1: Executive Control Tower</h4>
          <p style="margin: 0.5rem 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.45;">
            Welcome to the <strong>Executive Control Tower</strong>! This dashboard aggregates all active transit shipments across India.
            <br/>🔍 <strong>What to Look For & Highlight:</strong>
            <ul style="margin: 0.4rem 0 0; padding-left: 1.2rem;">
              <li><strong>Value at Risk</strong>: Highlights the total invoice cost of cargo currently exposed to storms or severe traffic.</li>
              <li><strong>Live Shipment Map</strong>: Look at the Plotly map showing active freight lanes connecting major cargo cities.</li>
              <li><strong>AI Action Queue</strong>: Review the table at the bottom where the AI automatically prioritizes shipments and recommends recovery actions (e.g., rerouting or advancing dispatch).</li>
            </ul>
          </p>
        </div>
        """, unsafe_allow_html=True)
    elif page == "Digital Twin Simulator":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a, #0d9488); padding: 1.2rem; border-radius: 14px; border-left: 6px solid #38bdf8; margin-bottom: 1.2rem; color: white;">
          <h4 style="margin: 0; color: white; font-size: 1.15rem;">🧭 Tour Guide • Stop 2: What-if Digital Twin Simulator</h4>
          <p style="margin: 0.5rem 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.45;">
            Welcome to the <strong>Digital Twin Simulator</strong>! Here, you can simulate transit scenarios before dispatching vehicles.
            <br/>🛠️ <strong>Try This Highlighted Action:</strong>
            <ol style="margin: 0.4rem 0 0; padding-left: 1.2rem;">
              <li>Adjust the sliders to set <strong>Weather: Storm</strong> and <strong>Traffic: Severe</strong>.</li>
              <li>Observe the <strong>SLA Probability</strong> and <strong>Predicted Delay</strong> meters update in real-time.</li>
              <li>The system will compare the Baseline case side-by-side with your scenario and issue a <strong>Recommended Action</strong> (e.g., advance dispatches to avoid severe delays).</li>
            </ol>
          </p>
        </div>
        """, unsafe_allow_html=True)
    elif page == "Network Intelligence":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a, #0d9488); padding: 1.2rem; border-radius: 14px; border-left: 6px solid #38bdf8; margin-bottom: 1.2rem; color: white;">
          <h4 style="margin: 0; color: white; font-size: 1.15rem;">🧭 Tour Guide • Stop 3: Network Relationship Graph</h4>
          <p style="margin: 0.5rem 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.45;">
            Welcome to <strong>Network Intelligence</strong>! This page maps connections between suppliers, warehouses, and customers.
            <br/>🛠️ <strong>Try This Highlighted Action:</strong>
            <ol style="margin: 0.4rem 0 0; padding-left: 1.2rem;">
              <li>Look at the visual graph layout connecting supply chain nodes.</li>
              <li>In the dropdown under the graph, select <strong>Chennai Hub</strong> to simulate a complete hub failure.</li>
              <li>The AI will analyze graph paths, identify blocked inbound lines from suppliers, and recommend <strong>dynamic rerouting plans</strong> for affected customers (e.g., diverting Retail A to Delhi Hub).</li>
            </ol>
          </p>
        </div>
        """, unsafe_allow_html=True)
    elif page == "AI Copilot":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a, #0d9488); padding: 1.2rem; border-radius: 14px; border-left: 6px solid #38bdf8; margin-bottom: 1.2rem; color: white;">
          <h4 style="margin: 0; color: white; font-size: 1.15rem;">🧭 Tour Guide • Stop 4: Conversational AI Copilot</h4>
          <p style="margin: 0.5rem 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.45;">
            Welcome to the <strong>AI Copilot</strong>! Ask business and tracking questions in plain, conversational English without needing complex lookup tools.
            <br/>🛠️ <strong>Try This Highlighted Action:</strong>
            <ol style="margin: 0.4rem 0 0; padding-left: 1.2rem;">
              <li>Select the sample question: <strong>"What happens if the Chennai warehouse closes?"</strong> or type your own question about order status (e.g., <em>"where is order ORD-1001"</em>).</li>
              <li>Click <strong>Analyse</strong> to view the parsed response. The stateful agent translates your request, pulls live tracking/dispatch data from the database, and reports ETAs and driver contacts in plain English.</li>
            </ol>
          </p>
        </div>
        """, unsafe_allow_html=True)
    elif page == "Data Governance & MDM":
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e3a8a, #0d9488); padding: 1.2rem; border-radius: 14px; border-left: 6px solid #38bdf8; margin-bottom: 1.2rem; color: white;">
          <h4 style="margin: 0; color: white; font-size: 1.15rem;">🧭 Tour Guide • Stop 5: Data Cleaning, Quality & Compliance</h4>
          <p style="margin: 0.5rem 0 0; color: #e2e8f0; font-size: 0.92rem; line-height: 1.45;">
            Welcome to the **Data Cleaning & Operations** page! Here, you monitor how uncleaned device logs are processed into certified, dashboard-ready metrics.
            <br/>🛠️ <strong>Try This Highlighted Action:</strong>
            <ol style="margin: 0.4rem 0 0; padding-left: 1.2rem;">
              <li>Click <strong>Run Ingestion Pipeline</strong>. This runs raw records through Bronze, cleans formats in Silver, and updates the PostgreSQL database.</li>
              <li>Observe the <strong>Latest Certified Business Metrics</strong> populate automatically once the run succeeds.</li>
              <li>Inspect the <strong>Quality Auditing Rules</strong> to see how the system ensures data boundaries and integrity.</li>
            </ol>
          </p>
        </div>
        """, unsafe_allow_html=True)

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
    if role == "Executive (Admin)":
        c4.metric("Value at Risk", f"₹{exposure/1e6:.1f}M")
    else:
        c4.metric("Value at Risk", "🔒 Restricted")
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
    if role != "Executive (Admin)":
        action_df["shipment_value_inr"] = "🔒 [Restricted]"
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
    if role == "Executive (Admin)":
        d.metric("Estimated Cost", f"₹{scenario.estimated_cost_inr:,.0f}")
    else:
        d.metric("Estimated Cost", "🔒 Restricted")
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
    if role != "Executive (Admin)":
        comparison = comparison[comparison["Metric"] != "Cost (₹000)"]
        
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
        
        affected_suppliers = [n for n in affected if G.nodes[n]["type"] == "Supplier"]
        affected_customers = [n for n in affected if G.nodes[n]["type"] == "Customer"]
        
        # Build dynamic AI mitigation recommendations
        response_lines = []
        response_lines.append(f"**AI Resiliency & Mitigation Analysis for {disrupted}:**\n")
        
        if affected_suppliers:
            response_lines.append(f"⚠️ **Inbound Supply Lines Blocked**: Direct supply from **{', '.join(affected_suppliers)}** is cut off. Action: Pause purchase orders or redirect supplier transport lanes.")
            
        if affected_customers:
            response_lines.append(f"🚨 **Outbound SLA Risk**: Deliveries to **{', '.join(affected_customers)}** are immediately disrupted.")
            response_lines.append("👉 **Re-Routing Actions**:")
            for cust in affected_customers:
                other_hubs = [h for h in G.neighbors(cust) if h != disrupted and G.nodes[h]["type"] == "Warehouse"]
                if other_hubs:
                    response_lines.append(f"  - Divert **{cust}** shipments to **{', '.join(other_hubs)}** which has active, healthy links.")
                else:
                    fallback_mapping = {
                        "Enterprise C": "Mumbai Hub (Emergency Corridor)",
                        "Retail B": "Bengaluru Hub (Emergency Corridor)"
                    }
                    fallback = fallback_mapping.get(cust, "the nearest operational warehouse")
                    response_lines.append(f"  - **{cust}** has no direct redundant hub paths. Establish an emergency transit corridor from **{fallback}**.")
                    
        priority_mapping = {
            "Delhi Hub": "Delhi Hub manages North zone fulfillment. Divert shipments through NH-48 via Mumbai and check if West-region suppliers can cover priority orders.",
            "Mumbai Hub": "Mumbai Hub is the primary Western gateway. Immediately re-route premium consignments to Pune/Ahmedabad storage depots and trigger local carrier contingency lanes.",
            "Bengaluru Hub": "Bengaluru Hub coordinates South zone technology and manufacturing parts. Shift picking queue to Chennai Hub and notify Retailers of potential 4-6 hour delay windows.",
            "Chennai Hub": "Chennai Hub faces elevated weather risk. Divert South-bound shipments to Bengaluru Hub or Hyderabad corridor, and prioritize high-value life-saving medicines first."
        }
        
        response_lines.append(f"\n💡 **Strategic Recommendation**: {priority_mapping.get(disrupted, 'Reassign orders to the nearest healthy hub and protect premium-customer SLAs first.')}")
        
        st.warning("\n".join(response_lines))

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
            answer = answer_copilot(question, shipments, warehouses, user_role=role)
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
    st.subheader("Data Cleaning, Quality & System Operations")
    st.caption("Monitor the data journey from raw fleet feeds to certified business metrics, ensure data accuracy, and inspect operational protocols.")
    
    import data_pipeline
    
    # 1. Ingestion & Synchronization Control
    col1, col2 = st.columns([1, 1.25])
    with col1:
        st.markdown("### Ingestion & Synchronization Control")
        st.info("Trigger a complete data synchronization cycle. This reads raw GPS pings from the fleet, validates and cleans formats, and computes overall business KPIs.")
        if st.button("Run Ingestion Pipeline", type="primary", use_container_width=True):
            with st.spinner("Executing pipeline cleaning cycles..."):
                kpi_data = data_pipeline.execute_full_pipeline()
                if kpi_data:
                    st.success("Data synchronization completed successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Synchronization failed. Check server logs.")
                    
        # Display folder stats
        bronze_count = len(list(data_pipeline.BRONZE_DIR.glob("*.json"))) if data_pipeline.BRONZE_DIR.exists() else 0
        silver_count = len(list(data_pipeline.SILVER_DIR.glob("*.csv"))) if data_pipeline.SILVER_DIR.exists() else 0
        gold_exists = (data_pipeline.GOLD_DIR / "kpi_dashboard.json").exists()
        
        st.markdown("#### Data Storage Summary")
        st.markdown(f"- 📁 **Raw Inputs Zone (Unchecked logs)**: `{bronze_count}` batch file(s) collected")
        st.markdown(f"- 📁 **Cleaned Database Zone (Validated records)**: `{silver_count}` batch file(s) verified")
        st.markdown(f"- 📁 **Business Report Zone (Dashboard ready)**: `{'1' if gold_exists else '0'}` certified report")
        
    with col2:
        st.markdown("### The Medallion Data Journey")
        # Visual diagram of the architecture using HTML/CSS
        st.markdown("""
        <div style="background: rgba(128,128,128,0.1); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
            <div style="flex: 1; padding: 0.5rem; background: #3b2314; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #d97706;">Raw Stage (Bronze)</strong><br/>
              <span style="font-size: 0.75rem; color: #f59e0b;">Uncleaned truck sensor feeds.</span>
            </div>
            <div style="color: #cbd5e1;">➔</div>
            <div style="flex: 1; padding: 0.5rem; background: #1e293b; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #94a3b8;">Clean Stage (Silver)</strong><br/>
              <span style="font-size: 0.75rem; color: #cbd5e1;">Errors removed & saved to DB.</span>
            </div>
            <div style="color: #cbd5e1;">➔</div>
            <div style="flex: 1; padding: 0.5rem; background: #133b1e; border-radius: 8px; margin: 0 4px;">
              <strong style="color: #16a34a;">Business Stage (Gold)</strong><br/>
              <span style="font-size: 0.75rem; color: #4ade80;">Certified metrics computed.</span>
            </div>
          </div>
          <div style="margin-top: 1rem; font-size: 0.85rem; color: #94a3b8; line-height: 1.45;">
            <strong>System Status</strong>: <code>Healthy & Online</code><br/>
            <strong>Ingestion Feed Source</strong>: Continuous mock streaming (<code>shipments.csv</code>)<br/>
            <strong>Storage Location</strong>: Secured local enterprise folders (S3-compatible bucket simulation)
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display preview of Gold KPI if exists in plain English
        gold_path = data_pipeline.GOLD_DIR / "kpi_dashboard.json"
        if gold_path.exists():
            st.markdown("#### Latest Certified Business Metrics")
            try:
                with open(gold_path, "r") as f:
                    kpi_data = json.load(f)
                
                # Format ISO timestamp to readable date-time
                raw_time = kpi_data.get("kpi_timestamp", "")
                readable_time = raw_time.split(".")[0].replace("T", " ") if raw_time else "N/A"
                
                st.markdown(f"🗓️ **Last Calculation Time**: `{readable_time}`")
                
                c_kpi1, c_kpi2 = st.columns(2)
                with c_kpi1:
                    st.metric("Total Active Shipments", f"{kpi_data.get('total_active_shipments', 0)}")
                    st.metric("Delayed Cargo Units", f"{kpi_data.get('delayed_count', 0)}")
                    st.metric("Average Transit Delay", f"{kpi_data.get('average_predicted_delay_hours', 0.0)} Hours")
                with c_kpi2:
                    st.metric("Active Assets Value", f"₹{kpi_data.get('total_value_inr', 0)/1e6:.2f}M")
                    st.metric("Delay Incurrence Rate", f"{kpi_data.get('delay_rate_percentage', 0.0)}%")
                    
                    risk_info = kpi_data.get('risk_category_counts', {})
                    critical_count = risk_info.get('Critical', 0)
                    st.metric("Critical Risk Consignments", f"{critical_count}")
            except Exception as e:
                st.info("Failed to display metrics preview. Please run the Ingestion Pipeline first.")
            
    st.divider()
    
    # 2. Master Data Management & Auditing
    st.markdown("### Master Data Management & Quality Auditing Rules")
    st.info("The system automatically checks every record against corporate data policies. Below are the current active data quality rules:")
    
    audit_left, audit_right = st.columns(2)
    with audit_left:
        st.markdown("#### Outbound Logistics Quality Rules")
        st.markdown("""
        - ✅ **Unique Shipment Identifier**
          - *Rule*: Every active shipment record must possess a valid, non-empty tracking code.
        - ✅ **GPS Boundary Validity Check**
          - *Rule*: Location latitudes and longitudes must fall strictly within the geopolitical borders of India.
        """)
    with audit_right:
        st.markdown("#### Operational Integrity Rules")
        st.markdown("""
        - ✅ **Dispatch Link Integrity**
          - *Rule*: All transit shipments must have an assigned driver name, vehicle registration number, and contact number.
        - ✅ **Delay Log Allocation**
          - *Rule*: Any shipment marked as 'Delayed' must have an accompanying delay reason and recovery action in the database.
        """)
        
    st.divider()
    
    # 3. Security Operations Protocol Guide
    st.markdown("### Data Security & Remote Operations Guide")
    st.info("Below is the operational protocol for secure remote administration, file transfers, and server connectivity explained in plain English.")
    
    ssh_left, ssh_right = st.columns(2)
    with ssh_left:
        st.markdown("#### Security Key Generation & Remote Login")
        st.markdown("""
        1. **Create Digital Security Keys**
           - Administrators generate a pair of unique cryptographic security keys (specifically an Ed25519 key pair). This provides robust security, far stronger than standard text passwords.
        2. **Authorize the Key on the Server**
           - The administrator's public security key is copied to the remote logistics server's approved list.
        3. **Connect Securely to the Server**
           - Connects the administrator's local computer directly to the remote server using the private security key, establishing a secure encrypted management session.
        4. **Audit Container Status**
           - Evaluates the virtual servers running on the machine (like PostgreSQL and Kafka) to ensure all services are healthy and running.
        """)
        
    with ssh_right:
        st.markdown("#### Port Forwarding & Secure File Transfer")
        st.markdown("""
        1. **Establish Secure Port Tunneling**
           - Binds the remote server's messaging channels (port 9092) and admin interface (port 8080) directly to your local computer's ports. This allows secure local administration as if the server was on your desk.
        2. **Verify Port Connection**
           - Checks the active connection tunnels to ensure events are streaming successfully without interruptions.
        3. **Safe File Upload (Secure Copy)**
           - Uploads raw shipment files directly from the operator's computer into the Bronze storage zone of the remote server.
        4. **Back up Business KPI Reports**
           - Downloads the certified Gold analytical summary report from the remote server's secure storage to local back-up repositories.
        """)
