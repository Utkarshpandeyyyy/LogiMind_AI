
from __future__ import annotations
from dataclasses import dataclass, asdict
import pandas as pd

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

def answer_copilot(question: str, shipments: pd.DataFrame, warehouses: pd.DataFrame) -> str:
    q = question.lower().strip()

    if "highest risk" in q or "most risky" in q:
        row = shipments.sort_values("risk_score", ascending=False).iloc[0]
        return (
            f"{row.shipment_id} has the highest risk score at {row.risk_score}/100. "
            f"It is travelling from {row.origin} to {row.destination}. "
            f"Primary drivers are {row.weather.lower()} weather and {row.traffic.lower()} traffic. "
            f"Recommended action: reroute and reserve a backup vehicle."
        )

    if "chennai" in q and ("close" in q or "closed" in q or "flood" in q):
        impacted = shipments[
            (shipments.origin.eq("Chennai")) | (shipments.destination.eq("Chennai"))
        ]
        exposure = int(impacted.shipment_value_inr.sum())
        return (
            f"Closing Chennai affects {len(impacted)} active shipments with approximately "
            f"₹{exposure:,.0f} in value. Recommended plan: redirect critical orders to Bengaluru, "
            f"move standard orders to Hyderabad, and notify customers with SLA risk above 50%."
        )

    if "delayed" in q:
        delayed = shipments[shipments.status.eq("Delayed")]
        return (
            f"There are {len(delayed)} delayed shipments. "
            f"The average predicted delay is {delayed.predicted_delay_hours.mean():.1f} hours. "
            f"Most common controllable cause: traffic and warehouse congestion."
        )

    if "warehouse" in q and "risk" in q:
        risky = warehouses.sort_values("capacity_pct", ascending=False).iloc[0]
        return (
            f"{risky.warehouse} is currently the most stressed hub at "
            f"{risky.capacity_pct}% capacity. Recommended action: divert new inbound volume "
            f"to the nearest hub until utilisation falls below 80%."
        )

    if "save" in q or "cost" in q:
        high_risk = shipments[shipments.risk_score >= 60]
        potential = int(high_risk.shipment_value_inr.sum() * 0.035)
        return (
            f"Prioritising the {len(high_risk)} highest-risk shipments could protect roughly "
            f"₹{potential:,.0f} in avoidable penalties and expedited-delivery cost."
        )

    return (
        "I can analyse shipment risk, delayed orders, warehouse stress, disruption scenarios, "
        "potential savings and Chennai-warehouse closure impact. Try asking: "
        "'Which shipment has the highest risk?'"
    )
