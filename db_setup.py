import time
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
import random

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "shipments.csv"
WH_CSV_PATH = BASE_DIR / "data" / "warehouses.csv"

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password",
    "dbname": "logimind"
}

def wait_for_db(retries=10, delay=3):
    """Wait for Postgres connection to become available."""
    print("Waiting for Postgres database to start...")
    for i in range(retries):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            conn.close()
            print("Successfully connected to Postgres database!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Postgres not ready yet (Attempt {i+1}/{retries})...")
            time.sleep(delay)
    print("Error: Could not connect to Postgres database.")
    return False

def setup_database():
    if not wait_for_db():
        return False
        
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    
    # 1. Drop existing tables if they exist
    print("Dropping existing tables...")
    cur.execute("DROP TABLE IF EXISTS orders CASCADE;")
    cur.execute("DROP TABLE IF EXISTS vehicles CASCADE;")
    cur.execute("DROP TABLE IF EXISTS shipments CASCADE;")
    cur.execute("DROP TABLE IF EXISTS warehouses CASCADE;")
    
    # 2. Create tables
    print("Creating tables...")
    
    # Shipments table
    cur.execute("""
    CREATE TABLE shipments (
        shipment_id VARCHAR(50) PRIMARY KEY,
        origin VARCHAR(100) NOT NULL,
        destination VARCHAR(100) NOT NULL,
        distance_km DOUBLE PRECISION NOT NULL,
        weather VARCHAR(50) NOT NULL,
        traffic VARCHAR(50) NOT NULL,
        priority VARCHAR(50) NOT NULL,
        vehicle_health VARCHAR(50) NOT NULL,
        warehouse_load VARCHAR(50) NOT NULL,
        shipment_value_inr DOUBLE PRECISION NOT NULL,
        base_eta_hours DOUBLE PRECISION NOT NULL,
        predicted_delay_hours DOUBLE PRECISION NOT NULL,
        risk_score INT NOT NULL,
        status VARCHAR(50) NOT NULL,
        origin_lat DOUBLE PRECISION NOT NULL,
        origin_lon DOUBLE PRECISION NOT NULL,
        destination_lat DOUBLE PRECISION NOT NULL,
        destination_lon DOUBLE PRECISION NOT NULL
    );
    """)
    
    # Warehouses table
    cur.execute("""
    CREATE TABLE warehouses (
        warehouse VARCHAR(100) PRIMARY KEY,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        capacity_pct INT NOT NULL
    );
    """)
    
    # Orders table
    cur.execute("""
    CREATE TABLE orders (
        order_id VARCHAR(50) PRIMARY KEY,
        shipment_id VARCHAR(50) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
        customer_name VARCHAR(100) NOT NULL,
        item_name VARCHAR(150) NOT NULL,
        quantity INT NOT NULL,
        current_location VARCHAR(200) NOT NULL,
        estimated_delivery VARCHAR(100) NOT NULL,
        status VARCHAR(50) NOT NULL,
        delay_reason VARCHAR(250) NOT NULL,
        mitigation_action VARCHAR(250) NOT NULL
    );
    """)
    
    # Vehicles & Drivers table
    cur.execute("""
    CREATE TABLE vehicles (
        shipment_id VARCHAR(50) PRIMARY KEY REFERENCES shipments(shipment_id) ON DELETE CASCADE,
        vehicle_number VARCHAR(50) NOT NULL,
        driver_name VARCHAR(100) NOT NULL,
        driver_phone VARCHAR(50) NOT NULL
    );
    """)
    
    # 3. Populate Shipments
    print("Populating shipments table...")
    df = pd.read_csv(CSV_PATH)
    shipment_records = [tuple(x) for x in df.to_numpy()]
    insert_shipment_query = """
    INSERT INTO shipments (
        shipment_id, origin, destination, distance_km, weather, traffic, priority,
        vehicle_health, warehouse_load, shipment_value_inr, base_eta_hours,
        predicted_delay_hours, risk_score, status, origin_lat, origin_lon,
        destination_lat, destination_lon
    ) VALUES %s;
    """
    execute_values(cur, insert_shipment_query, shipment_records)
    
    # 4. Populate Warehouses
    print("Populating warehouses table...")
    wh_df = pd.read_csv(WH_CSV_PATH)
    wh_records = [tuple(x) for x in wh_df.to_numpy()]
    insert_wh_query = """
    INSERT INTO warehouses (warehouse, latitude, longitude, capacity_pct) VALUES %s;
    """
    execute_values(cur, insert_wh_query, wh_records)
    
    # 5. Populate Orders and Vehicles mapping from shipments
    print("Generating orders and vehicles details...")
    orders = []
    vehicles = []
    
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
    
    # For each shipment, generate:
    # - 1 or 2 orders
    # - 1 vehicle/driver mapping
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
        vehicles.append((shp_id, reg_num, driver[0], driver[1]))
        
        # Order location description
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
        
        # Create 1-2 orders
        num_orders = random.randint(1, 2)
        for _ in range(num_orders):
            cust = random.choice(customers)
            item = random.choice(items)
            qty = random.randint(1, 5)
            
            order_id = f"ORD-{order_counter}"
            order_counter += 1
            
            orders.append((
                order_id, shp_id, cust, item[0], qty * item[1], 
                location, est_deliv, status, delay_reason, mitigation_action
            ))
            
    # Insert Orders
    print(f"Inserting {len(orders)} orders...")
    insert_order_query = """
    INSERT INTO orders (
        order_id, shipment_id, customer_name, item_name, quantity, 
        current_location, estimated_delivery, status, delay_reason, mitigation_action
    ) VALUES %s;
    """
    execute_values(cur, insert_order_query, orders)
    
    # Insert Vehicles
    print(f"Inserting {len(vehicles)} vehicles...")
    insert_vehicle_query = """
    INSERT INTO vehicles (shipment_id, vehicle_number, driver_name, driver_phone) VALUES %s;
    """
    execute_values(cur, insert_vehicle_query, vehicles)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database schema created and populated successfully!")
    return True

if __name__ == "__main__":
    setup_database()
