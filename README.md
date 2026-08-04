
# LogiMind AI

**Autonomous Supply Chain Decision Intelligence**

A fully running hackathon MVP that demonstrates:

- Executive logistics control tower
- Shipment risk and delay analytics
- Digital twin what-if simulation
- Business-action recommendations
- Supply-chain relationship graph
- Executive AI copilot
- Cost, carbon and SLA impact analysis

## 1. Install Python

Install Python 3.10 or newer.

## 2. Open the project

Open the `LogiMind_AI` folder in Visual Studio Code.

## 3. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

## 5. Run

```bash
streamlit run app.py
```

The browser should open automatically. Otherwise open:

```text
http://localhost:8501
```

## Suggested demo flow

1. Open **Executive Control Tower** and show value at risk.
2. Open **Digital Twin Simulator**.
3. Set:
   - Weather: Storm
   - Traffic: Severe
   - Warehouse load: Overloaded
   - Warehouse closed: On
4. Explain how the system compares baseline vs disruption.
5. Open **Network Intelligence** and fail Chennai Hub.
6. Open **AI Copilot** and ask:
   - What happens if the Chennai warehouse closes?
   - Which shipment has the highest risk?

## Pitch

Most supply-chain tools only show alerts. LogiMind AI goes further:

**Predict → Simulate → Recommend → Explain**

The prototype uses simulated data. A production deployment can connect to ERP, WMS, GPS, weather, traffic, IoT, fleet and supplier systems.
