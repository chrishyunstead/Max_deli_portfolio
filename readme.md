# Delivus Delivery MAX Predictor

> Korean version: [README_Kver.md](./README_Kver.md)

## Production MLOps System for Predicting Regional Delivery Capacity

This project predicts the total delivery time by region, weekday, and delivery volume using operational data from the company database.  
It then combines the prediction output with driver schedules and regional available working time to automatically calculate the maximum feasible delivery capacity, called **MAX**.

The generated MAX values are used as upstream inputs for the Postalcode Clustering Lambda, helping reduce over-assignment and under-assignment by driver and improving same-day delivery SLA stability.

---

## Executive Impact

| Metric | Before | After | Impact |
|---|---:|---:|---|
| MAX calculation | Experience-based manual decision | ML-based automated calculation | Automated operational decision-making |
| SLA | 97.15% | 97.93% | **+0.78% improvement** |
| Baseline update | Manual | Daily automatic update | Improved freshness |
| Clustering input | Fixed / experience-based values | Prediction-based MAX | Better delivery volume balance |
| Operations workload | Manual calculation and review | Google Sheets auto-update | Reduced operational burden |

---

## Business Problem

In same-day delivery operations, it is critical to estimate how many items each driver can realistically handle in a day.

- If MAX is set too high, too many deliveries are assigned to a driver, increasing the risk of delay.
- If MAX is set too low, driver resources are underutilized and operational efficiency decreases.
- Regional delivery difficulty, weekday patterns, delivery volume, and fixed/FLEX driver schedules need to be considered together.
- It was difficult to manually calculate and update the latest capacity baseline immediately before clustering.

Therefore, MAX was not just a reference value. It was a key operational parameter that directly affected clustering quality and SLA stability.

---

## My Role

I implemented the full pipeline end-to-end, from data loading to model inference and operational output.

- Configured Lambda VPC settings to connect directly to the company database
- Designed and preprocessed the operational dataset for training and inference
- Developed a regional total delivery time prediction model based on region, weekday, and volume
- Implemented a LightGBM-based batch inference pipeline
- Designed MAX calculation logic by combining prediction output with driver available time
- Implemented fixed-driver and FLEX-driver capacity distribution logic
- Deployed the system using AWS SAM Image-based Lambda
- Configured daily automation through EventBridge Scheduler
- Integrated Google Sheets API to update the operations-facing output automatically
- Connected the generated output as upstream data for Postalcode Clustering Lambda

---

## Core Process

### 1. Direct Database Integration

VPC Subnet and Security Group settings were configured in `template.yaml` so that AWS Lambda could directly access the internal company database.

```text
AWS Lambda
  → VPC Subnet / Security Group
  → Company DB
  → Historical Operation Data Load
```

### 2. Feature Engineering

Operational data is transformed into a model-ready dataset.

| Feature | Description |
|---|---|
| Area | Delivery region |
| Weekday | Weekday-based delivery volume and productivity pattern |
| Volume | Number of delivery items by region |
| Driver Schedule | Fixed/FLEX driver availability |
| Total Delivery Time | Target variable predicted by the model |

### 3. Model Training / Inference

A LightGBM regression model predicts total delivery time under different regional, weekday, and volume conditions.

### 4. MAX Calculation

The predicted total delivery time is combined with available driver working time to calculate the feasible delivery capacity.

```text
Regional total volume
→ Predicted total delivery time
→ Capacity calculation against available driver time
→ Fixed / FLEX driver MAX allocation
→ Final MAX output
```

### 5. Daily Automation

```text
EventBridge Scheduler
        ↓
MAX Predictor Lambda
        ↓
DB Data Load
        ↓
Model Inference / MAX Calculation
        ↓
Google Sheets Update
        ↓
Postalcode Clustering Lambda Input
```

### 6. Operational Output

The operations team can check the latest MAX values in Google Sheets immediately before clustering.

![MAX Shipping Result](./docs/images/image1.png)

---

## Architecture

```text
EventBridge Scheduler
        ↓
AWS Lambda (SAM Image)
        ↓
VPC / Subnet / Security Group
        ↓
Company DB
        ↓
Feature Engineering
        ↓
LightGBM Batch Inference
        ↓
MAX Capacity Calculation
        ↓
Google Sheets API Update
        ↓
Postalcode Clustering Lambda Input
```

---

## Tech Stack

| Category | Stack |
|---|---|
| Language | Python |
| ML | LightGBM, Scikit-learn |
| Data | Pandas, NumPy |
| Infrastructure | AWS Lambda, AWS SAM, Docker Image |
| Scheduler | EventBridge |
| Database | MySQL, PostgreSQL |
| Output | Google Sheets API |
| Monitoring | CloudWatch Logs |

---

## Repository Structure

```text
Max_deli_portfolio/
├── README.md
├── template.yaml
├── Dockerfile
├── app.py
├── requirements.txt
├── events/
├── src/
│   ├── data/
│   ├── features/
│   ├── model/
│   ├── predict/
│   └── sheets/
└── docs/
    └── images/
        └── image1.png
```

---

## Why This Is Strong MLOps Experience

- Built a data pipeline that directly connects to the company database
- Automated the workflow from feature engineering to batch inference and operational output
- Connected a serverless ML system to real operational decision-making
- Integrated the output with a downstream clustering system
- Measured and improved performance using operational KPIs

---

## Security / Redaction

The following items were removed or replaced with sample values for the public portfolio repository.

- Actual database credentials
- Actual AWS Account ID / VPC information
- Actual Google Sheets ID
- Some internal table names
- Deployment-only `samconfig.toml`

---

## Key Takeaway

> I converted an experience-based driver capacity decision into an ML-driven AWS automation pipeline, improving SLA stability and clustering quality in a real production operation.
