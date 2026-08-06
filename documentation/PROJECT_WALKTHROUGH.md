# SCDI – Supply Chain Disruption Intelligence: Final Project Walkthrough

This document serves as the final walkthrough of **SCDI (Supply Chain Disruption Intelligence)**. It defines the core problems facing modern supply chains, details how SCDI solves them, and provides a step-by-step demonstration flow.

---

## 1. The Core Problems in Supply Chain Logistics

Global supply chains are highly complex and vulnerable to disruptions. Most freight operations suffer from four critical challenges:

* **Reactive vs. Proactive Planning**: Traditional logistics control towers are historical reporting tools. They tell managers that a shipment is late *after* it has already missed its delivery slot, leaving no time to react.
* **Invisible Financial Exposure**: Planners can see where trucks are, but they cannot easily aggregate the monetary value of shipments passing through risky areas. They cannot prioritize shipments based on financial impact.
* **Lack of Scenario Simulation**: If a storm is brewing, managers cannot test how diverting routes or using alternate hubs affects shipping times, transport costs, and carbon footprints before committing.
* **Data and Communication Silos**: Finding simple answers (like *"Which hub is running at maximum capacity?"*) requires logging into ERP databases, sorting spreadsheets, or calling dispatchers, slowing down responses during a crisis.

---

## 2. What SCDI Solves: Key Capabilities

SCDI addresses these gaps by shifting supply chain operations from simple tracking to **Decision Intelligence**.

### Feature 1: Executive Control Tower
* **What it solves**: Integrates geographical tracking with financial metrics. The dashboard displays **Value at Risk** (exposure) and **Network SLA** alongside a Plotly map displaying shipment paths across major cities (Delhi, Mumbai, Bengaluru, Chennai, Hyderabad, Kolkata).
* **Business Benefit**: Allows executives to focus attention and budget on protecting high-value cargo under disruption.

### Feature 2: Digital Twin Scenario Simulator
* **What it solves**: Runs mathematical transit simulations ([engine.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/engine.py#L30)) before dispatch. Users can adjust sliders for distance, weather (Clear, Storm), traffic (Low, Severe), warehouse load, and vehicle health to immediately compare baseline metrics vs. simulated metrics.
* **Business Benefit**: Estimates delays, costs, and carbon impact ahead of time, outputting a precise recommended action (e.g. advance dispatches or alternative highway routing).

### Feature 3: Network Intelligence
* **What it solves**: Maps the physical connection between Suppliers, Warehouses, and Customers as a Graph database model using NetworkX. Operators can select a hub failure (e.g., Chennai Hub) to instantly list affected nodes.
* **Business Benefit**: Visualizes network dependency, enabling quick backup routing and mitigating regional supply shortages.

### Feature 4: Executive AI Copilot
* **What it solves**: Provides a simple conversational interface (`answer_copilot` in [engine.py](file:///c:/Users/utkar/OneDrive/Desktop/LogiMind_AI/engine.py#L106)) that parses queries. Users can ask standard questions like *"Which shipment has the highest risk?"* or *"How many shipments are delayed?"*.
* **Business Benefit**: Empowers operational team members to make data-driven decisions without needing SQL training.

---

## 3. Step-by-Step MVP Demonstration Flow

To demonstrate the full capability of the SCDI MVP, run the app using `streamlit run app.py` and follow these steps:

1. **Step 1: Open the Control Tower Dashboard**
   - Review the metrics row. Note the **Value at Risk** showing exposure.
   - Point out the active cargo lines across India on the Mapbox visualization.
   - Scroll down to review the **AI Action Queue** showing automated prioritizations and recommendations.
2. **Step 2: Run a What-If Scenario**
   - Click **Digital Twin Simulator** in the sidebar.
   - Set Weather to **Storm**, Traffic to **Severe**, and Warehouse Load to **Overloaded**.
   - Compare the Scenario metrics against the Baseline cards and review the recommended action block.
3. **Step 3: Test Network Resiliency**
   - Click **Network Intelligence** in the sidebar.
   - Under *Simulate node failure*, select **Chennai Hub**.
   - Note the immediate listing of directly impacted customers and suppliers.
4. **Step 4: Consult the AI Copilot**
   - Click **AI Copilot** in the sidebar.
   - Ask: *"What happens if the Chennai warehouse closes?"*.
   - Click **Analyse** to view the parsed response and supporting shipment data table.
