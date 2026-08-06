import re
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

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

# 2. Classify and Generate SQL Node
def classify_and_generate_sql(state: AgentState) -> AgentState:
    query = state["query"]
    q_lower = query.lower()
    
    # Extract Order ID or Shipment ID using Regex (e.g. ORD-1001 or SHP-1001 or standard shipment codes)
    order_id_match = re.search(r'\b(ord-\d+|shp-\d+)\b', q_lower)
    order_id = order_id_match.group(0).upper() if order_id_match else None
    
    if not order_id:
        return {
            **state,
            "order_id": None,
            "response": "Could you please provide a valid Order ID (e.g., ORD-1001) or Shipment ID (e.g., SHP-1001) to track your delivery?"
        }
        
    # Determine Query Intent
    intent = "details"  # default
    if any(x in q_lower for x in ["where", "location", "right now", "current", "find"]):
        intent = "location"
    elif any(x in q_lower for x in ["how long", "time", "deliver", "eta", "when"]):
        intent = "delivery_time"
    elif any(x in q_lower for x in ["why", "reason", "cause"]):
        intent = "delay_reason"
    elif any(x in q_lower for x in ["what should i do", "action", "mitigat", "handle", "solve", "overcome"]):
        intent = "mitigation"
    elif any(x in q_lower for x in ["vehicle", "driver", "truck", "phone", "number", "contact", "details"]):
        intent = "vehicle_driver"
        
    # Generate SQL query depending on intent
    # Note: query uses both order_id or shipment_id for user convenience
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
    # If prior node already set a response (e.g. no order_id found), bypass
    if state.get("response"):
        return state
        
    sql = state["sql_query"]
    order_id = state["order_id"]
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute query with order_id for both query parameters (matches order_id or shipment_id)
        cur.execute(sql, (order_id, order_id))
        result = cur.fetchall()
        
        cur.close()
        conn.close()
        
        if not result:
            return {
                **state,
                "db_result": None,
                "response": f"Sorry, I couldn't find any order or shipment matching **{order_id}** in our active logistics database."
            }
            
        return {
            **state,
            "db_result": result
        }
    except Exception as e:
        return {
            **state,
            "db_result": None,
            "response": f"Operational Database Error: Could not retrieve tracking details. Please ensure the database container is running. Error: {e}"
        }

# 4. Generate Response Node
def generate_response(state: AgentState) -> AgentState:
    if state.get("response"):
        return state
        
    result = state["db_result"][0]  # Take first match
    intent = state["intent"]
    order_id = result.get("order_id", state["order_id"])
    shipment_id = result.get("shipment_id", "")
    
    response = ""
    if intent == "details":
        response = (
            f"### Order Details for **{order_id}** (Shipment: `{shipment_id}`)\n\n"
            f"- **Customer Name**: {result['customer_name']}\n"
            f"- **Item Ordered**: {result['item_name']} (Qty: {result['quantity']})\n"
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

# Add Nodes
workflow.add_node("classify", classify_and_generate_sql)
workflow.add_node("query_db", execute_sql)
workflow.add_node("respond", generate_response)

# Set Entry and Edges
workflow.set_entry_point("classify")
workflow.add_edge("classify", "query_db")
workflow.add_edge("query_db", "respond")
workflow.add_edge("respond", END)

# Compile Graph
order_agent_graph = workflow.compile()

def process_order_query(query: str) -> str:
    """Invokes the LangGraph compiled state flow for order-specific tracking."""
    initial_state = {
        "query": query,
        "order_id": None,
        "intent": None,
        "sql_query": None,
        "db_result": None,
        "response": None
    }
    result = order_agent_graph.invoke(initial_state)
    return result["response"]
