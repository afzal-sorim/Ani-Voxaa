import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# -----------------------------
# CONFIG
# -----------------------------
PROD_FILE = "production.csv"
ALERT_FILE = "alerts.csv"
FORECAST_FILE = "forecast.csv"
TASK_FILE = "tasks.csv"

plants = [
    "Dearborn", "Chicago", "Detroit", "Kansas City",
    "Louisville", "Valencia", "Cologne", "Chennai"
]

models = [
    "F-150", "Mustang", "Explorer", "Escape", "Edge",
    "Ranger", "Bronco", "Expedition", "Fusion", "Mach-E"
]

departments = [
    "Assembly", "Paint Shop", "Body Shop",
    "Quality Check", "Logistics"
]

teams = ["Team 1", "Team 2", "Team 3", "Team 4"]

# -----------------------------
# HELPERS
# -----------------------------
def get_week(date):
    return f"W{date.isocalendar().week:02d}"

def get_quarter(month):
    return f"Q{(month-1)//3 + 1}"

# -----------------------------
# LOAD DATA
# -----------------------------
prod = pd.read_csv(PROD_FILE)
alerts = pd.read_csv(ALERT_FILE)
forecast = pd.read_csv(FORECAST_FILE)
tasks = pd.read_csv(TASK_FILE)

prod["Date"] = pd.to_datetime(prod["Date"])

last_date = prod["Date"].max()
today = last_date + timedelta(days=1)

# -----------------------------
# 1. PRODUCTION UPDATE
# -----------------------------
new_prod = []

for plant in plants:
    for model in models:
        
        base = 160 + (models.index(model) * 5)
        
        # weekend drop
        if today.weekday() >= 5:
            base *= 0.85
        
        # plant variation
        plant_factor = 1 + (plants.index(plant) * 0.02)
        
        units = int(base * plant_factor * np.random.uniform(0.95, 1.05))
        revenue = units * 500
        
        dept = np.random.choice(departments)
        
        new_prod.append([
            today.strftime("%Y-%m-%d"),
            get_week(today),
            today.month,
            get_quarter(today.month),
            plant,
            dept,
            model,
            units,
            revenue
        ])

new_prod_df = pd.DataFrame(new_prod, columns=prod.columns)
prod = pd.concat([prod, new_prod_df], ignore_index=True)
prod.to_csv(PROD_FILE, index=False)

print("✅ Production updated")

# -----------------------------
# 2. ALERTS (TIED TO PRODUCTION)
# -----------------------------
new_alerts = []

for _, row in new_prod_df.iterrows():
    
    # probability of alert based on production volume
    if np.random.rand() < 0.6:
        
        affected = int(row["Units"] * np.random.uniform(0.05, 0.15))
        
        severity = np.random.choice(
            ["Low", "Medium", "High"],
            p=[0.3, 0.4, 0.3]
        )
        
        status = np.random.choice(
            ["Active", "Resolved"],
            p=[0.6, 0.4]
        )
        
        issue = np.random.choice([
            "Machine Failure",
            "Quality Issue",
            "Equipment Failure",
            "Safety Issue",
            "Inspection Failure"
        ])
        
        new_alerts.append([
            row["Date"],
            row["Week"],
            row["Plant"],
            row["Department"],
            issue,
            severity,
            affected,
            status
        ])

new_alerts_df = pd.DataFrame(new_alerts, columns=alerts.columns)
alerts = pd.concat([alerts, new_alerts_df], ignore_index=True)
alerts.to_csv(ALERT_FILE, index=False)

print("✅ Alerts updated")

# -----------------------------
# 3. FORECAST (ROLLING AVG + WEEKLY UPDATE)
# -----------------------------
# use last 7 days avg per model
recent = prod.tail(7 * len(plants) * len(models))

forecast_rows = []

for plant in plants:
    for model in models:
        
        subset = recent[
            (recent["Plant"] == plant) &
            (recent["Model"] == model)
        ]
        
        if len(subset) == 0:
            continue
        
        avg_units = subset["Units"].mean()
        
        # slight upward trend
        forecast_units = int(avg_units * np.random.uniform(1.01, 1.05))
        forecast_revenue = forecast_units * 500
        
        forecast_rows.append([
            today.strftime("%Y-%m-%d"),
            get_week(today),
            plant,
            np.random.choice(departments),
            model,
            forecast_units,
            forecast_revenue
        ])

new_forecast_df = pd.DataFrame(forecast_rows, columns=forecast.columns)
forecast = pd.concat([forecast, new_forecast_df], ignore_index=True)
forecast.to_csv(FORECAST_FILE, index=False)

print("✅ Forecast updated")

# -----------------------------
# 4. TASKS UPDATE
# -----------------------------
new_tasks = []

for plant in plants:
    
    if np.random.rand() < 0.5:
        
        dept = np.random.choice(departments)
        
        task = np.random.choice([
            "Calibration", "Inspection", "Repair",
            "Optimization", "Audit", "Upgrade"
        ])
        
        priority = np.random.choice(
            ["Low", "Medium", "High"],
            p=[0.2, 0.5, 0.3]
        )
        
        status = np.random.choice([
            "Scheduled", "In Progress", "Completed", "Delayed"
        ])
        
        new_tasks.append([
            f"T{len(tasks)+len(new_tasks)+1}",
            today.strftime("%Y-%m-%d"),
            get_week(today),
            plant,
            dept,
            task,
            "Maintenance",
            priority,
            status,
            np.random.choice(teams)
        ])

new_tasks_df = pd.DataFrame(new_tasks, columns=tasks.columns)
tasks = pd.concat([tasks, new_tasks_df], ignore_index=True)
tasks.to_csv(TASK_FILE, index=False)

print("✅ Tasks updated")

print(f"🎯 ALL DATASETS UPDATED FOR {today.strftime('%Y-%m-%d')}")