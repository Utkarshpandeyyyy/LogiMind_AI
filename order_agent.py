import re
import psycopg2
import pandas as pd
import random
from pathlib import Path
from psycopg2.extras import RealDictCursor
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

BASE_DIR = Path(__file__).parent

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password",
    "dbname": "logimind"
}

# 1. Define Agent State
class AgentState(TypedDict):
    query: str
    order_id: Optional[str]
    intent: Optional[str]
    sql_query: Optional[str]
    db_result: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    user_role: Optional[str]

def ensure_static_tables():
    """Generates orders.csv and vehicles.csv deterministically if they do not exist."""
    orders_csv = BASE_DIR / "data" / "orders.csv"
    vehicles_csv = BASE_DIR / "data" / "vehicles.csv"
    
    if orders_csv.exists() and vehicles_csv.exists():
        return pd.read_csv(orders_csv), pd.read_csv(vehicles_csv)
        
    shipments_csv = BASE_DIR / "data" / "shipments.csv"
    if not shipments_csv.exists():
        return pd.DataFrame(), pd.DataFrame()
        
    df = pd.read_csv(shipments_csv)
    
    # Save random state to prevent side effects
    rand_state = random.getstate()
    random.seed(42)  # Set deterministic seed
    
    customers = [
        "Amit Verma", "Neha Sharma", "Rajesh Patel", "Priya Iyer", 
        "Suresh Nair", "Karan Johar", "Vikram Rathore", "Deepika Padukone",
        "Sunil Gavaskar", "Aravind Swamy", "Anil Kapoor", "Shweta Tiwari",
        "Rahul Dravid", "Rohan Bopanna", "Preeti Zinta", "Sachin Tendulkar",
        "Sania Mirza", "Mary Kom", "Mahendra Singh Dhoni", "Virat Kohli"
    ]
    
    items = [
        ("Smartphones (5G)", 450), ("Laptops (Intel i7)", 120), 
        ("Solar Inverters", 15), ("Life-saving Medicines", 2500), 
        ("Automotive Engine Valves", 800), ("Organic Cotton Textiles", 300),
        ("Lithium-Ion Battery Packs", 60), ("Precision Drill Tools", 400),
        ("High-End Audio Speakers", 180), ("Industrial Safety Helmets", 1200)
    ]
    
    drivers = [
        ("Satish Yadav", "+91 98112 34567"), ("Harpreet Singh", "+91 99223 45678"),
        ("Manish Chaudhury", "+91 97334 56789"), ("Ramesh Kadam", "+91 95445 67890"),
        ("Jasbir Singh", "+91 94556 78901"), ("Gopal Das", "+91 93667 89012"),
        ("Vijay Mhatre", "+91 91778 90123"), ("Sanjay Dutt", "+91 98889 01234"),
        ("Anwar Shaikh", "+91 99990 12345"), ("Devendra Singh", "+91 96112 23344"),
        ("Baldev Singh", "+91 95223 34455"), ("Raghu Ram", "+91 94334 45566"),
        ("Subhash Ghai", "+91 93445 56677"), ("Pradeep Rawat", "+91 92556 67788"),
        ("Kartik Aryan", "+91 91667 78899"), ("Siddharth Malhotra", "+91 98778 89900")
    ]
    
    states = ["DL", "MH", "KA", "HR", "GJ", "UP", "TN", "AP", "TS", "WB"]
    
    orders = []
    vehicles = []
    
    order_counter = 1001
    for idx, row in df.iterrows():
        shp_id = row["shipment_id"]
        status = row["status"]
        delay_hrs = row["predicted_delay_hours"]
        eta_hrs = row["base_eta_hours"]
        
        # Vehicle details
        state_code = random.choice(states)
        reg_num = f"{state_code}-{random.randint(10, 99)}-{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}-{random.randint(1000, 9999)}"
        driver = random.choice(drivers)
        vehicles.append({
            "shipment_id": shp_id,
            "vehicle_number": reg_num,
            "driver_name": driver[0],
            "driver_phone": driver[1]
        })
        
        # Location description
        if status == "On Track":
            location = f"In transit from {row['origin']} to {row['destination']}, currently near {row['origin']} transit corridor."
            delay_reason = "No delay predicted. Route is clear."
            mitigation_action = "Maintain scheduled speed and route."
        elif status == "At Risk":
            location = f"In transit between {row['origin']} and {row['destination']}. Border congestion observed."
            delay_reason = f"Congestion or mild weather near {row['destination']} region."
            mitigation_action = "Priority sorting at destination hub."
        else:  # Delayed
            location = f"In transit. Stopped/delayed near {row['destination']} corridor."
            delay_reason = f"Delayed due to {row['weather'].lower()} weather and {row['traffic'].lower()} traffic."
            mitigation_action = (
                "Reroute through alternative corridor" if row["traffic"] in ["High", "Severe"]
                else "Shift warehouse dispatch" if row["warehouse_load"] == "Overloaded"
                else "Expedite shipment processing"
            )
            
        total_eta = eta_hrs + (delay_hrs if status == "Delayed" else 0)
        est_deliv = f"{round(total_eta, 1)} hours"
        
        num_orders = random.randint(1, 2)
        for _ in range(num_orders):
            cust = random.choice(customers)
            item = random.choice(items)
            qty = random.randint(1, 5)
            
            order_id = f"ORD-{order_counter}"
            order_counter += 1
            
            orders.append({
                "order_id": order_id,
                "shipment_id": shp_id,
                "customer_name": cust,
                "item_name": item[0],
                "quantity": qty * item[1],
                "current_location": location,
                "estimated_delivery": est_deliv,
                "status": status,
                "delay_reason": delay_reason,
                "mitigation_action": mitigation_action
            })
            
    # Restore random state
    random.setstate(rand_state)
    
    orders_df = pd.DataFrame(orders)
    vehicles_df = pd.DataFrame(vehicles)
    
    # Save to CSV files
    orders_csv.parent.mkdir(parents=True, exist_ok=True)
    orders_df.to_csv(orders_csv, index=False)
    vehicles_df.to_csv(vehicles_csv, index=False)
    
    return orders_df, vehicles_df

def execute_fallback_query(state: AgentState) -> AgentState:
    """Fallback search in static CSV files when local Postgres container is offline."""
    try:
        orders_df, vehicles_df = ensure_static_tables()
        shipments_csv = BASE_DIR / "data" / "shipments.csv"
        shipments_df = pd.read_csv(shipments_csv)
        
        order_id = state["order_id"]
        intent = state["intent"]
        
        if intent == "hub_orders":
            # order_id is matched_city (e.g. "Chennai")
            merged = pd.merge(orders_df, shipments_df, on="shipment_id", suffixes=('', '_shipment'))
            filtered = merged[
                (merged["origin"].str.lower() == order_id.lower()) | 
                (merged["destination"].str.lower() == order_id.lower()) |
                (merged["current_location"].str.lower().str.contains(order_id.lower()))
            ]
            
            if filtered.empty:
                return {
                    **state,
                    "db_result": None,
                    "response": f"I couldn't find any active orders associated with the **{order_id} Hub** in our offline backup files."
                }
                
            records = filtered.to_dict(orient="records")
            return {
                **state,
                "db_result": records
            }
            
        # Standard tracking query
        is_order = order_id.startswith("ORD-")
        if is_order:
            match_order = orders_df[orders_df["order_id"] == order_id]
            if match_order.empty:
                return {
                    **state,
                    "db_result": None,
                    "response": f"Sorry, I couldn't find any order matching **{order_id}** in our offline backup files."
                }
            shipment_id = match_order.iloc[0]["shipment_id"]
        else:
            match_shipment = shipments_df[shipments_df["shipment_id"] == order_id]
            if match_shipment.empty:
                return {
                    **state,
                    "db_result": None,
                    "response": f"Sorry, I couldn't find any shipment matching **{order_id}** in our offline backup files."
                }
            shipment_id = order_id
            match_order = orders_df[orders_df["shipment_id"] == shipment_id]
            if match_order.empty:
                match_order = pd.DataFrame([{
                    "order_id": f"ORD-MOCK",
                    "shipment_id": shipment_id,
                    "customer_name": "General Consignee",
                    "item_name": "Logistics Freight",
                    "quantity": 1,
                    "current_location": "In transit",
                    "estimated_delivery": "N/A",
                    "status": match_shipment.iloc[0]["status"],
                    "delay_reason": "N/A",
                    "mitigation_action": "N/A"
                }])
                
        match_vehicle = vehicles_df[vehicles_df["shipment_id"] == shipment_id]
        vehicle_num = match_vehicle.iloc[0]["vehicle_number"] if not match_vehicle.empty else "N/A"
        driver_name = match_vehicle.iloc[0]["driver_name"] if not match_vehicle.empty else "N/A"
        driver_phone = match_vehicle.iloc[0]["driver_phone"] if not match_vehicle.empty else "N/A"
        
        res = {
            "order_id": match_order.iloc[0]["order_id"],
            "shipment_id": shipment_id,
            "customer_name": match_order.iloc[0]["customer_name"],
            "item_name": match_order.iloc[0]["item_name"],
            "quantity": match_order.iloc[0]["quantity"],
            "current_location": match_order.iloc[0]["current_location"],
            "estimated_delivery": match_order.iloc[0]["estimated_delivery"],
            "status": match_order.iloc[0]["status"],
            "delay_reason": match_order.iloc[0]["delay_reason"],
            "mitigation_action": match_order.iloc[0]["mitigation_action"],
            "vehicle_number": vehicle_num,
            "driver_name": driver_name,
            "driver_phone": driver_phone
        }
        
        return {
            **state,
            "db_result": [res]
        }
    except Exception as ex:
        return {
            **state,
            "db_result": None,
            "response": f"Offline data error: Failed to parse static shipment files. Error: {ex}"
        }

# 2. Classify and Generate SQL Node
def classify_and_generate_sql(state: AgentState) -> AgentState:
    query = state["query"]
    q_lower = query.lower()
    
    # Extract Order ID or Shipment ID using Regex (e.g. ORD-1001 or SHP-1001)
    order_id_match = re.search(r'\b(ord-\d+|shp-\d+)\b', q_lower)
    order_id = order_id_match.group(0).upper() if order_id_match else None
    
    # Check for hub query if no order ID is found
    cities = ["delhi", "mumbai", "bengaluru", "chennai", "kolkata", "hyderabad"]
    matched_city = None
    for city in cities:
        if city in q_lower:
            matched_city = city.capitalize()
            break
            
    if not order_id and matched_city:
        # Hub orders query
        sql = """
            SELECT o.order_id, o.shipment_id, o.customer_name, o.item_name, o.quantity, 
                   o.status, s.origin, s.destination, o.current_location
            FROM orders o
            JOIN shipments s ON o.shipment_id = s.shipment_id
            WHERE s.origin = %s OR s.destination = %s OR o.current_location = %s;
        """
        return {
            **state,
            "order_id": matched_city,  # City name stored here
            "intent": "hub_orders",
            "sql_query": sql
        }
        
    if not order_id:
        return {
            **state,
            "order_id": None,
            "response": "Could you please provide a valid Order ID (e.g. ORD-1001) or ask about orders at a specific hub (e.g. 'orders at Chennai Hub')?"
        }
        
    # Determine Query Intent
    intent = "details"
    if any(x in q_lower for x in ["what should i do", "action", "mitigat", "handle", "solve", "overcome", "how to get", "on time", "fix", "speed up", "expedite"]):
        intent = "mitigation"
    elif any(x in q_lower for x in ["where", "location", "right now", "current", "find"]):
        intent = "location"
    elif any(x in q_lower for x in ["how long", "time", "deliver", "eta", "when"]):
        intent = "delivery_time"
    elif any(x in q_lower for x in ["why", "reason", "cause"]):
        intent = "delay_reason"
    elif any(x in q_lower for x in ["vehicle", "driver", "truck", "phone", "number", "contact", "details"]):
        intent = "vehicle_driver"
        
    # Generate SQL query depending on intent
    if intent == "details":
        sql = """
            SELECT o.order_id, o.shipment_id, o.customer_name, o.item_name, o.quantity, 
                   o.current_location, o.estimated_delivery, o.status, o.delay_reason, o.mitigation_action,
                   v.vehicle_number, v.driver_name, v.driver_phone
            FROM orders o
            LEFT JOIN vehicles v ON o.shipment_id = v.shipment_id
            WHERE o.order_id = %s OR o.shipment_id = %s;
        """
    elif intent == "location":
        sql = """
            SELECT order_id, shipment_id, current_location, status 
            FROM orders 
            WHERE order_id = %s OR shipment_id = %s;
        """
    elif intent == "delivery_time":
        sql = """
            SELECT order_id, estimated_delivery, status 
            FROM orders 
            WHERE order_id = %s OR shipment_id = %s;
        """
    elif intent == "delay_reason":
        sql = """
            SELECT order_id, status, delay_reason 
            FROM orders 
            WHERE order_id = %s OR shipment_id = %s;
        """
    elif intent == "mitigation":
        sql = """
            SELECT order_id, status, delay_reason, mitigation_action 
            FROM orders 
            WHERE order_id = %s OR shipment_id = %s;
        """
    elif intent == "vehicle_driver":
        sql = """
            SELECT o.order_id, o.shipment_id, v.vehicle_number, v.driver_name, v.driver_phone 
            FROM orders o
            JOIN vehicles v ON o.shipment_id = v.shipment_id
            WHERE o.order_id = %s OR o.shipment_id = %s;
        """
        
    return {
        **state,
        "order_id": order_id,
        "intent": intent,
        "sql_query": sql
    }

# 3. Database Execution Node
def execute_sql(state: AgentState) -> AgentState:
    if state.get("response"):
        return state
        
    sql = state["sql_query"]
    order_id = state["order_id"]
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if state["intent"] == "hub_orders":
            cur.execute(sql, (order_id, order_id, order_id))
        else:
            cur.execute(sql, (order_id, order_id))
            
        result = cur.fetchall()
        cur.close()
        conn.close()
        
        if not result:
            if state["intent"] == "hub_orders":
                return {
                    **state,
                    "db_result": None,
                    "response": f"I couldn't find any active orders associated with the **{order_id} Hub** at the moment."
                }
            return {
                **state,
                "db_result": None,
                "response": f"Sorry, I couldn't find any order or shipment matching **{order_id}** in our active database."
            }
            
        return {
            **state,
            "db_result": result
        }
    except Exception as e:
        # Fall back to local CSV querying if Postgres is offline
        return execute_fallback_query(state)

# 4. Generate Response Node
def generate_response(state: AgentState) -> AgentState:
    if state.get("response"):
        return state
        
    result_list = state["db_result"]
    intent = state["intent"]
    order_id = state["order_id"]
    user_role = state.get("user_role", "Guest (Viewer)")
    
    if intent == "hub_orders":
        response = f"### Active Orders at **{order_id} Hub**\n\n"
        response += f"I found **{len(result_list)}** active order(s) associated with {order_id} (as origin, destination, or current location):\n\n"
        for r in result_list:
            qty_str = f"₹{r['quantity']:,.0f}" if user_role == "Executive (Admin)" else "[🔒 Restricted]"
            response += (
                f"- **Order {r['order_id']}** ({r['customer_name']} - {r['item_name']}, Value: {qty_str})\n"
                f"  - Route: {r['origin']} ➔ {r['destination']}\n"
                f"  - Transit Status: **{r['status']}**\n"
                f"  - Current Location: *{r['current_location']}*\n"
                f"  - Assigned Driver: {r.get('driver_name', 'N/A')} ({r.get('driver_phone', 'N/A')})\n\n"
            )
        return {
            **state,
            "response": response
        }
        
    result = result_list[0]
    shipment_id = result.get("shipment_id", "")
    
    response = ""
    if intent == "details":
        qty_str = f"₹{result['quantity']:,.0f}" if user_role == "Executive (Admin)" else "[🔒 Restricted]"
        response = (
            f"### Order Details for **{order_id}** (Shipment: `{shipment_id}`)\n\n"
            f"- **Customer Name**: {result['customer_name']}\n"
            f"- **Item Ordered**: {result['item_name']} (Value: {qty_str})\n"
            f"- **Current Status**: **{result['status']}**\n"
            f"- **Last Known Coordinates/Location**: {result['current_location']}\n"
            f"- **Estimated Time to Delivery**: {result['estimated_delivery']}\n"
            f"- **Assigned Truck (Vehicle No)**: `{result.get('vehicle_number', 'N/A')}`\n"
            f"- **Driver Contact**: {result.get('driver_name', 'N/A')} ({result.get('driver_phone', 'N/A')})\n\n"
        )
        if result['status'] == "Delayed":
            response += f"> ⚠️ **Delay Reason**: {result['delay_reason']}\n"
            response += f"> 🛠️ **Mitigation Step**: {result['mitigation_action']}\n"
            
    elif intent == "location":
        response = (
            f"📦 **Order tracking for {order_id}**:\n"
            f"- **Current Location**: {result['current_location']}\n"
            f"- **Status**: `{result['status']}`"
        )
        
    elif intent == "delivery_time":
        response = (
            f"⏱️ **Delivery Estimate for {order_id}**:\n"
            f"- **Remaining ETA**: {result['estimated_delivery']}\n"
            f"- **Transit Status**: `{result['status']}`"
        )
        
    elif intent == "delay_reason":
        if result['status'] != "Delayed":
            response = f"✅ Order **{order_id}** is currently **{result['status']}**. No delay reason reported."
        else:
            response = (
                f"⚠️ **Delay analysis for {order_id}**:\n"
                f"- **Transit Status**: `Delayed`\n"
                f"- **Disruption Reason**: {result['delay_reason']}"
            )
            
    elif intent == "mitigation":
        if result['status'] != "Delayed":
            response = f"✅ Order **{order_id}** is currently **{result['status']}**. No mitigation action required."
        else:
            response = (
                f"🛠️ **Operational mitigation for {order_id}**:\n"
                f"- **Delay Cause**: {result['delay_reason']}\n"
                f"- **Assigned Dispatch Recovery Action**: {result['mitigation_action']}"
            )
            
    elif intent == "vehicle_driver":
        response = (
            f"🚚 **Logistics Dispatch for {order_id}** (Shipment: `{shipment_id}`):\n"
            f"- **Vehicle Number**: `{result['vehicle_number']}`\n"
            f"- **Assigned Driver**: {result['driver_name']}\n"
            f"- **Contact Number**: {result['driver_phone']}"
        )
        
    return {
        **state,
        "response": response
    }

# 5. Build StateGraph Workflow
workflow = StateGraph(AgentState)

workflow.add_node("classify", classify_and_generate_sql)
workflow.add_node("query_db", execute_sql)
workflow.add_node("respond", generate_response)

workflow.set_entry_point("classify")
workflow.add_edge("classify", "query_db")
workflow.add_edge("query_db", "respond")
workflow.add_edge("respond", END)

order_agent_graph = workflow.compile()

def process_order_query(query: str, user_role: str = "Guest (Viewer)") -> str:
    """Invokes the LangGraph compiled state flow for order-specific tracking."""
    initial_state = {
        "query": query,
        "order_id": None,
        "intent": None,
        "sql_query": None,
        "db_result": None,
        "response": None,
        "user_role": user_role
    }
    result = order_agent_graph.invoke(initial_state)
    return result["response"]
