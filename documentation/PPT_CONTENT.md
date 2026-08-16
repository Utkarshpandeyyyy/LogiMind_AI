# LogiMind AI Presentation Slides (Tech Stack)

Use the sections below to copy and paste directly into your presentation slides.

---

## **Slide 1: Technology Stack Architecture**
* **Presentation Title**: *High-performance, lightweight, and interactive decision intelligence architecture.*
* **Visual Structure (3-Tier Layout)**:
  * **Frontend (Presentation Layer)**:
    * **Streamlit (v1.35+)**: Renders the dynamic executive dashboards, simulators, and copilot chat views.
    * **HTML5/Custom CSS**: Embedded styling to create high-premium dark mode card designs and hero layouts.
  * **Middleware & AI (Logic Layer)**:
    * **LangGraph & LangChain**: Powers the stateful, cyclic AI Copilot agent for intent classification and text-to-SQL logic.
    * **NetworkX (v3.2)**: Models supply chain nodes (hubs, customers) and routes as a topological graph network.
    * **Pandas & NumPy**: Drives fast, vectorized in-memory data processing, delay simulations, and value-at-risk calculations.
  * **Storage & Infrastructure (Data Layer)**:
    * **PostgreSQL**: Relational database storing live shipments, warehouse metadata, customer orders, and vehicle details.
    * **Docker Compose**: Orchestrates PostgreSQL database and local development services containerization.

---

## **Slide 2: Frontend & Interactive GIS Maps**
* **Presentation Title**: *Real-time visualization and immersive user experience.*
* **Key Components**:
  * **Streamlit Framework**:
    * Eliminates separate JS/HTML frameworks to provide pure Python hot-reloading dashboard UI.
    * Uses session-state caching (`st.cache_data`) for fluid rendering of large shipment datasets.
  * **Plotly Mapbox Integration**:
    * Dynamically plots origins, destinations, and connecting freight lanes using `Scattermapbox`.
    * Visualizes delay severity using color-coded nodes (Low, Medium, High, Critical) in dark-mode style.
  * **Responsive Widgets**:
    * Sliders, metrics cards, and selectboxes allow executive operators to run instant multi-factor simulations.

---

## **Slide 3: Backend Database & Graph Network Topology**
* **Presentation Title**: *Relational transactional data coupled with network dependency graphs.*
* **Key Components**:
  * **PostgreSQL Database**:
    * Implements relational schema connecting `shipments` -> `orders` -> `vehicles` -> `warehouses`.
    * Ensures strict data integrity and structured queries for precise supply chain audits.
  * **NetworkX Topology Analysis**:
    * Models the physical logistics supply chain as a mathematical graph (nodes = hubs/warehouses, edges = shipping lanes).
    * Calculates graph connectivity to identify downstream vulnerabilities when critical hubs (e.g., Chennai Hub) fail.

---

## **Slide 4: Stateful AI Copilot (Natural Language Processing)**
* **Presentation Title**: *Text-to-SQL AI Agent for conversational supply chain tracking.*
* **Key Components**:
  * **LangGraph Orchestration**:
    * Builds a stateful agent graph (`AgentState`) that classifies user questions (ETA requests, delay root causes, vehicle details).
    * Bypasses static lookup tables with dynamic intent-driven routing.
  * **Text-to-SQL Engine**:
    * Converts conversational text into parametrized PostgreSQL queries (safeguarded from SQL injection).
    * Executes against live Postgres databases and translates SQL results back into human-friendly explanations.
