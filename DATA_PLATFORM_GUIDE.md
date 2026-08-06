# LogiMind AI: Data Engineering & Platform Guide

This document provides a conceptual overview, operation cheatsheets, and interview Q&As covering the core data platform technologies: **Docker Compose**, **Apache Kafka**, **Data Pipelines**, **SSH**, and **Data Lakes**.

---

## 1. Conceptual Architecture Overview

LogiMind AI uses a **Medallion Data Lake Architecture** to process incoming logistics feeds (like GPS logs and warehouse loads) into aggregated dashboards.

```
┌─────────────────┐       ┌────────────────┐       ┌─────────────────┐
│  Bronze (Raw)   │ ───>  │ Silver (Clean) │ ───>  │   Gold (KPIs)   │
│ Raw JSON feeds  │       │ Structured CSV │       │ Curated Aggs    │
│ (Kafka Ingest)  │       │ (De-duplicated)│       │ (Decision ready)│
└─────────────────┘       └────────────────┘       └─────────────────┘
```

1. **Docker Compose**: Orchestrates local services (Kafka, Zookeeper, and the Web UI) in isolated containers.
2. **Apache Kafka**: Acts as the real-time event streaming backbone. Trucks and sensors publish GPS logs to the `shipment-events` topic, which our ingestion pipeline consumes.
3. **Data Pipeline**: The logic that consumes the raw stream (Bronze), applies data cleaning, filtering, and schema verification (Silver), and aggregates metrics into KPI files (Gold).
4. **Data Lake**: The central file repository (simulated locally in `data_lake/` and structured as Bronze/Silver/Gold folders).
5. **SSH**: The secure gateway used to remote into production nodes, manage containers, tunnel ports (such as mapping remote Kafka to localhost), and perform secure file transfer (SCP/SFTP).

---

## 2. SSH Operations Cheatsheet

### Key Generation & Setup
* **Generate a new SSH key pair**:
  ```bash
  ssh-keygen -t ed25519 -b 4096 -C "admin@logimind.ai"
  # Generates private key (id_ed25519) and public key (id_ed25519.pub) in ~/.ssh/
  ```
* **Install Public Key on Server (Linux)**:
  ```bash
  ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server_ip
  # Or manually copy to the remote file: ~/.ssh/authorized_keys
  ```

### Remote Connection
* **Connect securely**:
  ```bash
  ssh -i ~/.ssh/id_ed25519 user@server_ip
  ```

### Port Forwarding (SSH Tunneling)
* **Access remote Kafka/UI securely from local machine**:
  ```bash
  # Map remote Kafka UI (8080) and broker (9092) to local ports
  ssh -L 8080:localhost:8080 -L 9092:localhost:9092 user@server_ip -N
  ```

### Secure File Transfer (SCP)
* **Copy a local file to the remote Data Lake**:
  ```bash
  scp ./data/shipments.csv user@server_ip:/opt/datalake/bronze/
  ```
* **Copy a directory from remote to local**:
  ```bash
  scp -r user@server_ip:/opt/datalake/gold/ ./local_gold_backup/
  ```

---

## 3. Interview Prep Q&A

### Category A: Docker Compose & Kafka

#### Q1: Why use Docker Compose for local Kafka development? Why is Zookeeper needed?
* **Answer**: Running Kafka locally requires Zookeeper (for cluster state metadata, controller election, and topic configs) and Kafka brokers. Configuring these manually on Windows/macOS involves environment variables, JVM setups, and shell commands. Docker Compose lets us define all dependencies, networking, and ports in a single `docker-compose.yml` file and start the entire stack with one command: `docker compose up -d`.
* *Zookeeper note*: While modern Kafka supports KRaft (ZooKeeper-less mode), Zookeeper remains standard in enterprise environments for coordination.

#### Q2: Explain the difference between Kafka bootstrap servers and advertised listeners.
* **Answer**: 
  - **Bootstrap Servers** are a list of host/port pairs used by clients to establish an initial connection to the Kafka cluster.
  - **Advertised Listeners** are the addresses that Kafka returns to clients in metadata responses, informing them how to connect to the broker. If a broker is inside a Docker network, its internal address (e.g. `kafka:29092`) is used by other containers. If a client connects from the host machine, the broker must advertise its external localhost port (e.g., `localhost:9092`).

---

### Category B: Data Pipelines & Data Lakes

#### Q3: What is a Data Lake, and how does it differ from a Data Warehouse?
* **Answer**:
  - A **Data Lake** stores vast amounts of raw data in its native format (JSON, CSV, Parquet, logs, images) without a predefined schema. It supports a "schema-on-read" approach.
  - A **Data Warehouse** stores structured, cleaned, and modeled data optimized for query performance (SQL). It requires a "schema-on-write" approach.
  - In our architecture, the `data_lake/` directory houses raw feeds (Bronze), clean records (Silver), and analytical outputs (Gold), serving as a file-based Data Lake.

#### Q4: Why implement a Medallion Architecture (Bronze -> Silver -> Gold)?
* **Answer**: It enforces a data quality lifecycle:
  1. **Bronze (Raw)**: Ingests raw data at high velocity without modifications. If a pipeline failure occurs, we can replay raw events from Bronze without querying the source systems again.
  2. **Silver (Enriched/Cleaned)**: Performs data validation, schema enforcement, filtering of bad records, and null handling. This is the source of truth for ad-hoc queries.
  3. **Gold (Curated)**: Stores business-level aggregations and KPIs optimized for quick dashboard loading (like our Streamlit UI) and executive reporting.

---

### Category C: Infrastructure & SSH

#### Q5: How do you secure data pipeline nodes and Kafka brokers in production?
* **Answer**:
  1. **Network Isolation**: Hide Kafka brokers in a private subnet. Use SSH tunnels (`ssh -L`) or Bastion hosts to connect securely for administration.
  2. **SSH Authentication**: Disable password logins entirely. Enforce key-based SSH authentication (`id_ed25519` keys) and rotate them regularly.
  3. **Encryption in Transit**: Configure TLS/SSL for all client-to-broker and broker-to-broker communication in Kafka.
  4. **Access Control**: Enable SASL/SCRAM authentication for Kafka clients to regulate which producers/consumers can read or write to specific topics.
