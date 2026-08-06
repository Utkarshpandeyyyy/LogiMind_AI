import os
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

# Local Data Lake directories
BASE_DIR = Path(__file__).parent
DATA_LAKE_DIR = BASE_DIR / "data_lake"
BRONZE_DIR = DATA_LAKE_DIR / "bronze"
SILVER_DIR = DATA_LAKE_DIR / "silver"
GOLD_DIR = DATA_LAKE_DIR / "gold"
SOURCE_CSV = BASE_DIR / "data" / "shipments.csv"

# Ensure folders exist
for folder in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Optional Kafka client setup
HAS_KAFKA_CLIENT = False
try:
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable
    HAS_KAFKA_CLIENT = True
except ImportError:
    pass

def try_kafka_ingestion(records):
    """Attempts to publish records to Kafka if available."""
    if not HAS_KAFKA_CLIENT:
        return False, "kafka-python-ng not installed."
        
    producer = None
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=1000,
            max_block_ms=1000
        )
        print("Connected to local Kafka broker at localhost:9092. Streaming...")
        for r in records[:10]:  # Stream first 10 records as sample
            producer.send("shipment-events", r)
        producer.flush()
        producer.close()
        return True, "Successfully streamed 10 sample records to topic 'shipment-events'."
    except Exception as e:
        if producer:
            try:
                producer.close()
            except:
                pass
        return False, f"Kafka broker not reachable: {e}"

def run_bronze_layer():
    """Bronze Layer: Ingest Raw Data (JSON format) representing raw device feeds."""
    print("[Bronze] Running Bronze Ingestion Layer...")
    if not SOURCE_CSV.exists():
        print(f"Error: Source CSV not found at {SOURCE_CSV}")
        return []
    
    df = pd.read_csv(SOURCE_CSV)
    raw_records = df.to_dict(orient="records")
    
    # Save as raw JSON files in Bronze (representing raw event logs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bronze_file = BRONZE_DIR / f"raw_events_{timestamp}.json"
    
    # Clean up pandas nan to None
    clean_records = []
    for r in raw_records:
        clean_r = {k: (None if pd.isna(v) else v) for k, v in r.items()}
        clean_records.append(clean_r)
        
    with open(bronze_file, "w") as f:
        json.dump(clean_records, f, indent=2)
        
    print(f"Bronze Layer: Saved {len(clean_records)} raw records to {bronze_file.name}")
    
    # Try streaming to Kafka as well for live integration demonstration
    kafka_ok, kafka_msg = try_kafka_ingestion(clean_records)
    print(f"Kafka Ingestion Status: {kafka_msg}")
    
    return clean_records

def run_silver_layer():
    """Silver Layer: Read raw files from Bronze, parse schemas, clean and filter data."""
    print("[Silver] Running Silver Cleaning Layer...")
    bronze_files = sorted(BRONZE_DIR.glob("raw_events_*.json"))
    if not bronze_files:
        print("⚠️ No raw data in Bronze. Run Bronze ingestion first.")
        return []
        
    # Read latest raw file
    latest_raw = bronze_files[-1]
    with open(latest_raw, "r") as f:
        records = json.load(f)
        
    cleaned_records = []
    for r in records:
        # Clean and validate schema
        shipment_id = r.get("shipment_id", "").strip().upper()
        if not shipment_id:
            continue
            
        # Clean/standardize text fields
        origin = r.get("origin", "Unknown").strip()
        destination = r.get("destination", "Unknown").strip()
        priority = r.get("priority", "Standard").strip().capitalize()
        status = r.get("status", "On-Time").strip()
        
        # Ensure numerical types and defaults
        try:
            distance_km = float(r.get("distance_km", 0))
        except:
            distance_km = 0.0
            
        try:
            risk_score = int(r.get("risk_score", 0))
        except:
            risk_score = 0
            
        try:
            delay_hours = float(r.get("predicted_delay_hours", 0.0))
        except:
            delay_hours = 0.0
            
        try:
            value = float(r.get("shipment_value_inr", 0))
        except:
            value = 0.0
            
        cleaned_records.append({
            "shipment_id": shipment_id,
            "origin": origin,
            "destination": destination,
            "priority": priority,
            "status": status,
            "distance_km": distance_km,
            "risk_score": risk_score,
            "predicted_delay_hours": delay_hours,
            "shipment_value_inr": value,
            "processed_at": datetime.now().isoformat()
        })
        
    # Write to Silver (Cleaned CSV representation)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    silver_file = SILVER_DIR / f"cleaned_shipments_{timestamp}.csv"
    
    silver_df = pd.DataFrame(cleaned_records)
    silver_df.to_csv(silver_file, index=False)
    
    print(f"Silver Layer: Saved cleaned data to {silver_file.name}")
    return cleaned_records

def run_gold_layer():
    """Gold Layer: Read cleaned CSV from Silver, run aggregations, and compute KPIs."""
    print("[Gold] Running Gold Analytics Layer...")
    silver_files = sorted(SILVER_DIR.glob("cleaned_shipments_*.csv"))
    if not silver_files:
        print("⚠️ No cleaned data in Silver. Run Silver layer first.")
        return {}
        
    # Read latest cleaned file
    latest_cleaned = silver_files[-1]
    df = pd.read_csv(latest_cleaned)
    
    # Calculate analytical aggregates/KPIs
    total_value = float(df["shipment_value_inr"].sum())
    avg_delay = float(df["predicted_delay_hours"].mean())
    risk_profile = df["risk_score"].apply(
        lambda s: "Critical" if s >= 70 else ("High" if s >= 45 else ("Medium" if s >= 25 else "Low"))
    ).value_counts().to_dict()
    
    active_shipments = len(df)
    delayed_shipments = int((df["status"] == "Delayed").sum())
    delay_rate_pct = round((delayed_shipments / active_shipments) * 100, 1) if active_shipments > 0 else 0.0
    
    kpis = {
        "kpi_timestamp": datetime.now().isoformat(),
        "source_file": latest_cleaned.name,
        "total_active_shipments": active_shipments,
        "total_value_inr": total_value,
        "delayed_count": delayed_shipments,
        "delay_rate_percentage": delay_rate_pct,
        "average_predicted_delay_hours": round(avg_delay, 2),
        "risk_category_counts": risk_profile
    }
    
    # Write KPIs to Gold (Curated Business Insights)
    gold_file = GOLD_DIR / "kpi_dashboard.json"
    with open(gold_file, "w") as f:
        json.dump(kpis, f, indent=2)
        
    print(f"Gold Layer: Saved analytics dashboard to {gold_file.name}")
    return kpis

def execute_full_pipeline():
    """Runs all three layers of the pipeline sequentially."""
    print("=" * 60)
    print("Starting LogiMind Medallion Data Pipeline run...")
    print("=" * 60)
    
    start_time = time.time()
    
    raw = run_bronze_layer()
    if not raw:
        return None
        
    cleaned = run_silver_layer()
    if not cleaned:
        return None
        
    kpis = run_gold_layer()
    
    elapsed = time.time() - start_time
    print("=" * 60)
    print(f"Pipeline executed successfully in {elapsed:.2f} seconds!")
    print("=" * 60)
    return kpis

if __name__ == "__main__":
    execute_full_pipeline()
