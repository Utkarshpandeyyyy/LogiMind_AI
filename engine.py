from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd
import re

WEATHER_RISK = {"Clear": 0, "Rain": 2, "Heavy Rain": 6, "Storm": 10}
TRAFFIC_RISK = {"Low": 0, "Medium": 1.5, "High": 4, "Severe": 8}
VEHICLE_RISK = {"Good": 0, "Average": 2, "Poor": 5}
WAREHOUSE_RISK = {"Normal": 0, "Busy": 1.5, "Overloaded": 4}

@dataclass
class ScenarioResult:
    delay_hours: float
    risk_score: int
    estimated_cost_inr: int
    carbon_kg: float
    sla_probability_pct: int
    recommended_action: str
    explanation: str

def risk_level(score: float) -> str:
    if score >= 70:
        return "Critical"
    if score >= 45:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"

def simulate(
    distance_km: int,
    weather: str,
    traffic: str,
    vehicle_health: str,
    warehouse_load: str,
    priority: str,
    warehouse_closed: bool = False,
    fuel_increase_pct: int = 0,
) -> ScenarioResult:
    delay = (
        WEATHER_RISK[weather]
        + TRAFFIC_RISK[traffic]
        + VEHICLE_RISK[vehicle_health]
        + WAREHOUSE_RISK[warehouse_load]
    )

    if warehouse_closed:
        delay += 9

    if priority == "Critical":
        delay *= 0.82
    elif priority == "High":
        delay *= 0.92

    delay = round(max(0.0, delay), 1)
    risk = int(min(99, max(1, 10 + delay * 6)))

    base_cost = distance_km * 38
    cost = int(base_cost * (1 + fuel_increase_pct / 100))
    if warehouse_closed:
        cost += 18000

    carbon = round(distance_km * 0.72, 1)
    sla = int(max(5, min(99, 98 - delay * 6)))

    if warehouse_closed:
        action = "Shift fulfilment to the nearest healthy warehouse and split urgent shipments."
    elif traffic in ("High", "Severe"):
        action = "Reroute through the alternate corridor and reserve a backup vehicle."
    elif weather in ("Heavy Rain", "Storm"):
        action = "Advance dispatch, use weather-safe routing and notify premium customers."
    elif vehicle_health == "Poor":
        action = "Replace the vehicle before dispatch and preserve the original delivery slot."
    elif warehouse_load == "Overloaded":
        action = "Move picking to a nearby hub and prioritise critical orders."
    else:
        action = "Continue on the planned route with proactive monitoring."

    explanation = (
        f"Risk is driven by {weather.lower()} weather, {traffic.lower()} traffic, "
        f"{vehicle_health.lower()} vehicle condition and {warehouse_load.lower()} warehouse load. "
        f"The proposed action targets the largest controllable delay factor."
    )

    return ScenarioResult(
        delay_hours=delay,
        risk_score=risk,
        estimated_cost_inr=cost,
        carbon_kg=carbon,
        sla_probability_pct=sla,
        recommended_action=action,
        explanation=explanation,
    )

def recommend_for_row(row: pd.Series) -> dict:
    result = simulate(
        int(row["distance_km"]),
        str(row["weather"]),
        str(row["traffic"]),
        str(row["vehicle_health"]),
        str(row["warehouse_load"]),
        str(row["priority"]),
    )
    return asdict(result)

def validate_query(query: str) -> tuple[bool, str]:
    q_clean = query.lower().strip()
    words = set(re.findall(r'\b\w+\b', q_clean))
    
    # Check for tech terms
    tech_keywords = {
        'ssh', 'kafka', 'zookeeper', 'docker', 'compose', 'port', 'tunnel', 'keygen', 
        'python', 'code', 'git', 'architecture', 'medallion', 'pipeline', 'database', 
        'react', 'streamlit', 'framework', 'api', 'vm', 'virtual machine', 'cloud', 
        'ip address', 'server', 'deploy', 'cluster', 'table', 'query', 'sql', 'schema', 
        'branch', 'merge', 'commit', 'pull', 'push', 'repository', 'caching', 'cache', 
        'redis', 'fastapi', 'grpc', 'rest', 'frontend', 'backend', 'widget', 'slider', 
        'selectbox', 'button', 'javascript', 'sk-learn', 'scikit-learn', 'numpy', 'pandas', 
        'networkx', 'import', 'class', 'function', 'method', 'variable', 'loop', 'terminal', 
        'command', 'powershell', 'bash', 'script', 'linux', 'windows', 'key', 'keys', 
        'tunneling', 'scp'
    }
    
    matched_tech = words.intersection(tech_keywords)
    if matched_tech:
        return False, (
            "I cannot answer technical or programming questions (such as database schemas, "
            "Kafka, SSH, Docker, or code details). I only answer questions related to the business "
            "and operational work of the LogiMind AI project (orders, shipments, warehouses, delays, and routes)."
        )
        
    return True, ""

def answer_copilot(question: str, shipments: pd.DataFrame, warehouses: pd.DataFrame, user_role: str = "Guest (Viewer)") -> str:
    # First validate query to block technical questions
    is_valid, validation_msg = validate_query(question)
    if not is_valid:
        return validation_msg
        
    q = question.lower().strip()
    
    # 0. Check for user profile or role queries
    profile_keywords = ["my role", "my profile", "who am i", "my permissions", "my password", "what can i do", "what is my access", "about my profile", "clearance"]
    if any(x in q for x in profile_keywords):
        if user_role == "Executive (Admin)":
            return (
                f"### 🔒 User Profile: **Executive (Admin)**\n\n"
                f"- **Your Role**: Corporate Executive / System Administrator\n"
                f"- **Clearance Level**: Maximum (Full read-write access to all dashboards and operations)\n"
                f"- **Authorized Workspace Views**:\n"
                f"  1. `Executive Control Tower` (Financial exposures, live Plotly maps, value at risk)\n"
                f"  2. `Digital Twin Simulator` (What-if simulation engine and recommended actions)\n"
                f"  3. `Network Intelligence` (Network dependency graph and hub failure routing)\n"
                f"  4. `AI Copilot` (Conversational SQL tracking agent)\n"
                f"  5. `Data Governance & MDM` (Ingestion pipeline controls, data quality audits)\n"
                f"- **Authentication Secret**: `admin123` (Your secure password)\n\n"
                f"💡 *Executive Tip*: You have administrative power to run the medallion data pipeline on the operations page to sync fresh shipments into PostgreSQL."
            )
        elif user_role == "Logistics Operator":
            return (
                f"### 🚚 User Profile: **Logistics Operator**\n\n"
                f"- **Your Role**: Logistics Dispatch Operator\n"
                f"- **Clearance Level**: Medium (Authorized to simulate routes and track dispatches)\n"
                f"- **Authorized Workspace Views**:\n"
                f"  1. `Digital Twin Simulator` (Test environmental delays and alternative corridors)\n"
                f"  2. `Network Intelligence` (Trace supplier and customer dependencies)\n"
                f"  3. `AI Copilot` (Query live vehicle locations and driver contacts)\n"
                f"- **Authentication Secret**: `ops123` (Your secure password)\n\n"
                f"⚠️ *Access Alert*: You do not have permissions to access the Executive Control Tower (financial exposure dashboard) or the Data Governance control panel."
            )
        else: # Guest (Viewer)
            return (
                f"### 👁️ User Profile: **Guest (Viewer)**\n\n"
                f"- **Your Role**: Guest Auditor / Viewer\n"
                f"- **Clearance Level**: Minimum (View-only permissions for general reports)\n"
                f"- **Authorized Workspace Views**:\n"
                f"  1. `Executive Control Tower` (General metrics and live map)\n"
                f"  2. `Network Intelligence` (View supplier-customer graph topology)\n"
                f"- **Authentication Secret**: `guest123` (Your secure password)\n\n"
                f"⚠️ *Access Alert*: You are restricted from running digital twin simulations, asking the Copilot about vehicle/driver tracking databases, or modifying data ingestion pipelines."
            )

    # 1. Route order details, tracking, vehicle, driver, and delivery-related queries to PostgreSQL via LangGraph
    order_keywords = ["order", "track", "delivery", "vehicle", "driver", "where is", "how long", "delayed", "delay"]
    order_id_match = re.search(r'\b(ord-\d+|shp-\d+)\b', q)
    if order_id_match or any(x in q for x in order_keywords):
        from order_agent import process_order_query
        try:
            return process_order_query(question, user_role=user_role)
        except Exception as e:
            order_code = order_id_match.group(0).upper() if order_id_match else "your order"
            return (
                f"### Database Integration Status\n\n"
                f"I detected that you are asking about order tracking or dispatch details for **{order_code}**.\n\n"
                f"To resolve order tracking, driver contact information, and vehicle numbers in real-time, the system requires a Postgres database backend. "
                f"Please ensure you have started the database container using docker-compose and run the initialization script:\n"
                f"```bash\n"
                f"docker-compose up -d postgres\n"
                f"python db_setup.py\n"
                f"```\n\n"
                f"*Technical details: Connection to PostgreSQL failed ({e}).*"
            )
            
    # 2. Check for dynamic hub closures (any of the 4 hubs)
    matched_city = None
    for city in ["delhi", "mumbai", "bengaluru", "chennai"]:
        if city in q:
            matched_city = city.capitalize()
            break
            
    if matched_city and any(x in q for x in ["close", "closed", "flood", "failure", "offline", "shutdown", "stop", "shut", "down", "closure", "disrupt", "overcome"]):
        impacted = shipments[
            (shipments.origin.eq(matched_city)) | (shipments.destination.eq(matched_city))
        ]
        exposure = int(impacted.shipment_value_inr.sum())
        
        redirect_hubs = {
            "Delhi": "Mumbai Hub or Jaipur Hub",
            "Mumbai": "Delhi Hub or Bengaluru Hub",
            "Bengaluru": "Chennai Hub or Hyderabad Hub",
            "Chennai": "Bengaluru Hub or Hyderabad Hub"
        }
        fallback_hub = redirect_hubs.get(matched_city, "the nearest healthy hub")
        
        role_action = ""
        if user_role == "Executive (Admin)":
            role_action = "\n\n💡 **Executive Action**: You can run the data ingestion pipeline in the Data operations tab to clean and update these re-routed lanes in PostgreSQL."
        elif user_role == "Logistics Operator":
            role_action = "\n\n💡 **Operator Action**: Go to the What-if Simulator page to model this closure with alternate traffic and weather configurations."
        else:
            role_action = "\n\n💡 **Auditor Note**: Go to the Network Intelligence tab to view the visual graph topology of these connections."

        return (
            f"Simulating node closure for **{matched_city} Hub**:\n\n"
            f"- **Affected Shipments**: {len(impacted)} active route segments.\n"
            f"- **Financial Exposure**: ₹{exposure:,.0f} in transit value.\n"
            f"- **Mitigation Recommendation**: Redirect critical orders to {fallback_hub}, move standard orders to alternate hubs, and notify customers with SLA risk above 50%.{role_action}"
        )
        
    # 3. Check for Cost Optimization queries
    if "save" in q or "cost" in q or "optimis" in q or "optimiz" in q:
        high_risk = shipments[shipments.risk_score >= 60]
        potential = int(high_risk.shipment_value_inr.sum() * 0.035)
        
        role_action = ""
        if user_role == "Executive (Admin)":
            role_action = "\n\n💡 **Executive Action**: Audit the Value at Risk on the Control Tower to see which high-value contracts can be optimized today."
        elif user_role == "Logistics Operator":
            role_action = "\n\n💡 **Operator Action**: Coordinate with warehouse pickers and drivers to prevent hub congestion and avoid overtime costs."
        else:
            role_action = "\n\n💡 **Auditor Note**: Cost comparisons are visible in the Digital Twin case summaries."

        return (
            f"To optimize and boost logistics cost savings:\n\n"
            f"1. **Expedite High-Risk Shipments**: Prioritizing the **{len(high_risk)}** highest-risk shipments (Risk Score >= 60) can protect approximately **₹{potential:,.0f}** by avoiding SLA delay penalties.\n"
            f"2. **Dynamic Route Rerouting**: Rerouting vehicles around high-traffic or storm areas reduces fuel costs and delay penalties.\n"
            f"3. **Load Balancing**: Prevent warehouse overloading by shifting picking and fulfillment to less busy hubs, avoiding warehouse overtime costs.{role_action}"
        )
        
    # 4. Check if it matches other structured queries from the dashboard
    if "highest risk" in q or "most risky" in q:
        row = shipments.sort_values("risk_score", ascending=False).iloc[0]
        role_action = ""
        if user_role == "Executive (Admin)":
            role_action = f" As an **Executive**, you can authorize emergency dispatch resources to safeguard this shipment value (₹{row.shipment_value_inr:,.0f})."
        elif user_role == "Logistics Operator":
            role_action = " As an **Operator**, you should immediately notify driver " + row.shipment_id + " to switch to weather-safe routing."
        return (
            f"Active Shipment **{row.shipment_id}** currently presents the highest risk in the network at **{row.risk_score}/100**.\n\n"
            f"- **Route**: {row.origin} ➔ {row.destination}\n"
            f"- **Conditions**: Weather is {row.weather.lower()}, Traffic load is {row.traffic.lower()}.\n"
            f"- **Recommended Mitigation Action**: Reroute through alternative corridor and reserve a backup vehicle.{role_action}"
        )
        
    if "delayed" in q:
        delayed = shipments[shipments.status.eq("Delayed")]
        role_action = ""
        if user_role == "Executive (Admin)":
            role_action = "\n\n💡 **Executive Action**: Review late delivery penalties in your monthly SLA ledger."
        elif user_role == "Logistics Operator":
            role_action = "\n\n💡 **Operator Action**: Track individual delay reasons (like traffic or rain) by querying order details in the copilot."
        return (
            f"There are **{len(delayed)}** delayed shipments currently in transit.\n\n"
            f"- **Average Delay**: {delayed.predicted_delay_hours.mean():.1f} hours.\n"
            f"- **Top Controllable Causes**: Traffic congestion and warehouse load spikes.{role_action}"
        )
        
    if "warehouse" in q and "risk" in q:
        risky = warehouses.sort_values("capacity_pct", ascending=False).iloc[0]
        role_action = ""
        if user_role == "Executive (Admin)":
            role_action = "\n\n💡 **Executive Action**: Authorize expansion budget or divert new supplier contracts away from " + risky.warehouse + "."
        elif user_role == "Logistics Operator":
            role_action = "\n\n💡 **Operator Action**: Divert new logistics volume to the nearest healthy hub until capacity drops below 80%."
        return (
            f"The warehouse hub presenting the highest stress is **{risky.warehouse}** running at **{risky.capacity_pct}%** capacity.\n\n"
            f"- **Mitigation Action**: Divert new logistics volume to the nearest healthy hub until utilization drops below 80%.{role_action}"
        )
        
    # 5. Friendly operational fallback
    return (
        "I am the Virtual Pilot AI. I can answer questions regarding:\n"
        "- Your profile details, password, and permissions (e.g. 'what is my role')\n"
        "- Order details, current locations, and remaining ETA (e.g. 'where is order ORD-1001')\n"
        "- Driver contact details and vehicle numbers (e.g. 'who is the driver for order ORD-1002')\n"
        "- Delay reasons and operational mitigation steps (e.g. 'why is order ORD-1001 delayed')\n"
        "- Node failure simulations (e.g. 'what happens if Chennai Hub closes')\n"
        "- Savings and cost optimizations (e.g. 'how to cut costs')\n\n"
        "Please ask a question related to these operational topics."
    )
