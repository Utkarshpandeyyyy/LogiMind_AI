# SCDI – Supply Chain Disruption Intelligence Project Documentation

Welcome to the comprehensive reference guide for **SCDI (Supply Chain Disruption Intelligence)**, an AI-powered supply chain optimization platform. This document explains the codebase, the system architecture, and the overall project goals.

---

## 1. Codebase Explanation

The project consists of three core components: the web-based interactive front-end ([app.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/app.py)), the analytical and simulation backend engine ([engine.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/engine.py)), and the simulated datasets located in the `data/` folder.

### A. Frontend Application: [app.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/app.py)
This is the Streamlit-based web dashboard. It acts as the visual and interactive hub, structured as follows:

1. **Configurations and Custom Styling (Lines 13-40)**:
   - Sets the browser title to "LogiMind AI" (internal branding), enables a wide screen layout, and expands the sidebar by default.
   - Injects custom CSS rules via `st.markdown(..., unsafe_allow_html=True)` to styling containers, adjust metric text sizes, and construct a premium dark-themed landing card (`.hero` container).

2. **Data Caching & Loading (Lines 42-48)**:
   - Uses `@st.cache_data` to load data from [data/shipments.csv](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/data/shipments.csv) and [data/warehouses.csv](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/data/warehouses.csv).
   - caching ensures that the datasets are read only once at startup, optimizing re-render performance when state changes.

3. **Navigation and Sidebar Controls (Lines 50-61)**:
   - Renders radio buttons in the sidebar for switching between four main workspaces:
     - **Executive Control Tower**
     - **Digital Twin Simulator**
     - **Network Intelligence**
     - **AI Copilot**

4. **Executive Control Tower Page (Lines 73-165)**:
   - Calculates primary key performance indicators (KPIs): Total Shipments, Delayed Counts, Critical Risk Count (where risk score is $\ge 70$), Value at Risk (sum of shipment value for risk score $\ge 60$), and Network SLA (inversely proportional to average delay hours).
   - **Left Column**: Plots a geographic shipment network using Plotly Mapbox (`go.Scattermapbox`). It draws lines connecting the origin and destination of the first 35 active shipments, overlaying major Indian cargo cities (Delhi, Mumbai, Bengaluru, Chennai, Hyderabad, Kolkata).
   - **Right Column**: Uses Plotly Express to plot a vertical bar chart of shipment counts grouped by risk level (Low, Medium, High, Critical) and a horizontal bar chart displaying warehouse capacities.
   - **AI Action Queue**: Displays a tabular view of the top 10 highest-risk shipments, using lambda functions to recommend dynamic mitigations (e.g., rerouting or warehouse shifting) based on current weather/traffic conditions.

5. **Digital Twin Simulator Page (Lines 167-213)**:
   - Renders interactive widgets (sliders and selectboxes) representing shipment scenarios: distance, weather (Clear, Rain, Heavy Rain, Storm), traffic (Low, Medium, High, Severe), vehicle condition, warehouse loads, shipment priorities, warehouse closures, and fuel price escalation.
   - Compares the baseline simulation (Clear weather, Low traffic, Normal load, Good vehicle, 0% fuel hike) with the adjusted user scenario side-by-side using Streamlit metrics and a comparative Plotly grouped bar chart.

6. **Network Intelligence Page (Lines 215-270)**:
   - Construct a topological graph using `networkx.Graph` representing relationships between Suppliers, Warehouses/Hubs, and Retail/Enterprise Customers.
   - Computes node positions using the spring layout algorithm (`nx.spring_layout`).
   - Renders the node-edge topology using Plotly Scatter traces (`go.Scatter`).
   - Allows users to simulate a node failure (e.g., failing Chennai Hub) to instantly list affected downstream neighbors and output suggested recovery actions.

7. **AI Copilot Page (Lines 272-301)**:
   - Presents a conversational interface where users can select sample questions or type their own questions.
   - Calls the `answer_copilot` function to interpret queries and show real-time tabular evidence of high-risk shipments.

---

### B. Backend Engine: [engine.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/engine.py)
This script holds the mathematical logic and business rules:

1. **Risk Coefficients (Lines 6-9)**:
   - Defines static penalty weights for disruptions: weather delay hours (Storm has weight 10), traffic delays (Severe is 8), vehicle health (Poor is 5), and warehouse congestion (Overloaded is 4).

2. **Simulation Algorithm (Lines 30-93)**:
   - The function `simulate(...)` aggregates delay hours from all operational risk weights.
   - Adds a 9-hour penalty if a warehouse is closed.
   - Speeds up delivery times if priority is "High" (92%) or "Critical" (82%).
   - Calculates the **Risk Score** formula: $10 + (\text{delay hours} \times 6)$ bounded between 1 and 99.
   - Estimates shipment transport costs (₹38 per km) factoring in fuel cost adjustments and warehouse closure rerouting fees (₹18,000 flat penalty).
   - Generates a carbon footprint estimate (0.72 kg of $\text{CO}_2$ per km) and SLA reliability probability.
   - Selects a natural-language recommended action based on the dominant bottleneck (e.g., weather alerts trigger advance dispatches).

3. **AI Copilot Q&A Router (Lines 106-157)**:
   - Implements a string-matching routing mechanism (`answer_copilot`) to query the dataframes:
     - *Highest Risk*: Finds the shipment with the maximum risk score.
     - *Chennai Warehouse Closure*: Calculates the count and value of shipments touching Chennai.
     - *Delay Metrics*: Calculates average delays across affected orders.
     - *Warehouse stress*: Locates the hub operating at the highest capacity percentage.
     - *Save / cost*: Tallies shipments with risk scores $\ge 60$ and estimates savings assuming 3.5% of penalties are avoided.
     - *Default*: If no matches are found, it lists suggested query formats.

---

## 2. System Architecture

The architecture follows a modular, reactive design model.

```
       +---------------------------------------------+
       |             STREAMLIT FRONTEND              |
       |                (app.py)                     |
       +--------------------+------------------------+
                            |
           User Interactions| Requests & Datasets
           & Input Sliders  |
                            v
       +--------------------+------------------------+
       |             ANALYTICAL ENGINE               |
       |               (engine.py)                   |
       +--------------------+------------------------+
                            |
           Calculates Costs,| Risk Scores, 
           Delays & Actions | & Copilot Answers
                            v
       +--------------------+------------------------+
       |                DATABASES                    |
       |             (data/*.csv)                    |
       +---------------------------------------------+
```

### Key Architectural Concepts:
- **Reactive UI updates**: Streamlit re-executes the file from top to bottom on user input, updating the Plotly map and scenario statistics dynamically.
- **State-Cached reads**: Caching data loads prevents disk bottlenecks, keeping dashboard UI rendering times under 100ms.
- **Decoupled Business Logic**: Separation of frontend presentation ([app.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/app.py)) and simulation rules ([engine.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/engine.py)) allows testing the simulation engine independently of Streamlit.
- **Topological Graph Mapping**: Network relationships are isolated into memory using NetworkX, which dynamically traverses routes to calculate failure risks without heavy database joins.

---

## 3. Project Overview

**SCDI (Supply Chain Disruption Intelligence)** is designed to demonstrate how modern control tower systems shift from historical reporting to forward-looking predictive action.

### Core Value Pillars:
1. **Financial Risk Visualization**: By aggregating the value of shipments at risk (exposure), executives can prioritize intervention budgets based on real-time financial vulnerability.
2. **Interactive What-If Simulation**: Logistic managers can simulate a storm or bottleneck, evaluate the financial and environmental (carbon) cost of alternate routes, and coordinate backup carriers before the delay occurs.
3. **Automated Recommendations**: The tool replaces human guesswork by matching specific disruption patterns with targeted remedies (e.g., weather alerts trigger advance dispatches; traffic triggers alternate corridor routing).
4. **Conversational Intelligence**: An executive copilot enables non-technical team members to interrogate complex supply chain datasets using natural English commands, shortening response times during high-stakes events.

---

## 4. Understanding SCDI: A Guide for Non-Technical Stakeholders

If you do not write code, software systems can look like a collection of complicated terms. Here is a simple guide to understanding SCDI.

### The GPS Analogy: How SCDI Works
Think of SCDI like a **smart GPS app** (such as Google Maps or Waze) but built specifically for a company's shipping network.

1. **The Map (Executive Control Tower)**: Just like a GPS shows your current position and traffic colors (green, orange, red), the Control Tower page displays all the company's active shipments moving across India, highlighting which ones are on track and which ones are facing delays.
2. **The Route Planning (Digital Twin Simulator)**: Imagine you are planning a road trip, and you want to know what happens if a storm hits or if you get stuck in rush-hour traffic. Our Simulator lets you adjust these parameters beforehand. It calculates how many hours of delays you might face, how much extra fuel will cost, and suggests alternative actions (such as starting the trip early or taking a different route) before your trucks even leave the warehouse.
3. **The Backup Plan (Network Intelligence)**: If a major highway closes, a smart GPS will find a detour. The Network Intelligence page maps out how suppliers, regional hubs, and customer stores are linked. If a hub closes (due to weather or electricity issues), the system instantly identifies which customer stores will miss their deliveries and suggests alternate hubs to fulfill those orders.
4. **The Assistant (AI Copilot)**: Instead of clicking through buttons or search tools, you can type questions in plain English—just like talking to Siri or Alexa. Asking *"Which shipment is at the highest risk?"* prompts the assistant to analyze the data and report back with the exact truck ID, its current delay reason, and what to do next.

### Key Benefits to the Business:
* **Saves Money**: Identifies and protects high-value deliveries before penalties for late delivery are charged.
* **Improves Customer Service**: Helps you notify customers about delays ahead of time, or reroute their orders so they arrive on time.
* **Environmentally Friendly**: Tracks carbon emissions, helping the logistics team select routes that use less fuel and reduce emissions.
