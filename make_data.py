import pandas as pd
import numpy as np

# Set random seed so results are repeatable
np.random.seed(42)

browsers = ["Safari", "Chrome", "Firefox"]
devices = ["iOS", "Android", "Windows"]
gateways = ["ApplePay", "Stripe", "PayPal"]

rows = []

# 1. Normal period (Baseline)
for _ in range(250):
    browser = np.random.choice(browsers, p=[0.4, 0.5, 0.1])
    device = "iOS" if browser == "Safari" else np.random.choice(["Android", "Windows"])
    gateway = "ApplePay" if device == "iOS" else np.random.choice(["Stripe", "PayPal"])
    
    sessions = int(np.random.normal(500, 50))
    cr = 0.035  # 3.5% normal conversion rate
    orders = int(sessions * cr)
    revenue = orders * 75  # $75 average order
    
    rows.append({
        "period": "Baseline",
        "browser": browser,
        "device": device,
        "gateway": gateway,
        "sessions": sessions,
        "orders": orders,
        "revenue": revenue
    })

# 2. Incident period (ApplePay on iOS has a bug)
for _ in range(250):
    browser = np.random.choice(browsers, p=[0.4, 0.5, 0.1])
    device = "iOS" if browser == "Safari" else np.random.choice(["Android", "Windows"])
    gateway = "ApplePay" if device == "iOS" else np.random.choice(["Stripe", "PayPal"])
    
    sessions = int(np.random.normal(500, 50))
    # Apple Pay on iOS drops sharply to 0.5% conversion
    cr = 0.005 if (device == "iOS" and gateway == "ApplePay") else 0.035
    orders = int(sessions * cr)
    revenue = orders * 75
    
    rows.append({
        "period": "Incident",
        "browser": browser,
        "device": device,
        "gateway": gateway,
        "sessions": sessions,
        "orders": orders,
        "revenue": revenue
    })

df = pd.DataFrame(rows)
df.to_csv("store_data.csv", index=False)
print("SUCCESS: Created store_data.csv file!")