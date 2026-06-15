# Delivus Delivery MAX Predictor

> Korean version: [README_Kver.md](./README_Kver.md)

## Production MLOps System for Predicting Regional Delivery Capacity

This project is a production-oriented MLOps system that predicts the total delivery time by **volume, region, and weekday**, then combines the prediction with driver schedules and regional available working hours to calculate the operationally feasible **maximum delivery capacity (MAX)**.

The generated MAX values are used as upstream inputs for the **Postal Code Clustering Lambda**, helping reduce over-assignment and under-assignment per driver while improving same-day delivery SLA stability.

---

## Executive Impact

- **Automated operational decision-making**  
  Converted driver capacity estimation from experience-based manual judgment into a data-driven automated process.

- **Improved SLA stability**  
  By using predicted MAX values for dispatch planning, the overall delivery-area SLA improved from **97.15% to 97.93%**.

- **Improved clustering quality**  
  Automatically supplied the latest MAX values before the Postal Code Clustering Lambda runs, improving delivery volume balance across drivers.

- **Built a daily automated production pipeline**  
  Implemented a daily scheduled pipeline using **AWS Lambda + EventBridge**, with results automatically updated to Google Sheets.

- **Stable DB-connected operation**  
  Built a direct database pipeline that loads data from the company DB, performs training/inference, and reflects the results without relying on external BI tools.

---

## Business Problem

In same-day delivery operations, accurately estimating how many orders each driver can handle in a day is a critical operational decision.

If the MAX value is too high, too many deliveries may be assigned to a driver, causing delays.  
If the MAX value is too low, driver resources are underutilized, reducing operational efficiency.

The existing process had several limitations:

- MAX values were estimated manually based on operator experience.
- Regional delivery difficulty was hard to quantify.
- Weekday-specific demand and productivity patterns were not fully reflected.
- Fixed drivers and FLEX drivers required different capacity assumptions.
- The latest operational conditions were difficult to reflect immediately before clustering.
- Over-assignment and under-assignment caused SLA volatility.

Therefore, MAX was not just a reference metric. It was a key operational parameter that directly affected **delivery clustering quality and SLA stability**.

---

## Service Features

Delivery MAX Predictor performs the following tasks:

- Predicts total delivery time using historical delivery operation data from the company DB.
- Calculates MAX values based on region, weekday, delivery volume, and driver schedules.
- Combines predicted delivery time with regional available working hours.
- Automatically distributes MAX values between fixed drivers and FLEX drivers.
- Runs daily through **AWS Lambda Image + EventBridge**.
- Updates final output to **Google Sheets** automatically.
- Provides the generated MAX values as input data for the Postal Code Clustering Lambda.

---

## My Role

I implemented the project end-to-end, from data loading and model development to inference, deployment, and operational integration.

- Configured direct access to the company DB through Lambda VPC settings.
- Designed and preprocessed datasets for training and inference.
- Developed a model to predict total delivery time based on region, weekday, and volume.
- Implemented a **LightGBM-based prediction pipeline**.
- Designed MAX calculation logic by combining model predictions with driver availability.
- Implemented driver-schedule-based MAX distribution logic for fixed and FLEX drivers.
- Deployed the system using **AWS SAM Image-based Lambda**.
- Configured daily automated execution with **EventBridge Scheduler**.
- Integrated the output with **Google Sheets API** for the operations team.
- Connected the generated results to the downstream clustering system.

---

## Core Process

### 1. Direct DB Integration

The Lambda function was configured with VPC Subnet and Security Group settings in `template.yaml` to directly access the internal company database.

```text
AWS Lambda
  → VPC Subnet / Security Group
  → Company DB
  → Historical Operation Data Load
```

This allowed the system to perform training and inference using real operational data without manual file uploads or dependency on external BI tools.

---

### 2. Data Preprocessing and Training

The pipeline loads completed delivery history, region information, weekday data, driver schedules, and delivery volume from the company DB, then preprocesses the data into a model-ready format.

Example features:

| Feature | Description |
|---|---|
| Region | Delivery area or operational region |
| Weekday | Weekday-based volume and productivity pattern |
| Volume | Number of delivery items by region |
| Driver Schedule | Fixed driver / FLEX driver availability |
| Total Delivery Time | Target value predicted by the model |

The model uses **LightGBM** to predict total delivery time under different regional, weekday, and volume conditions.

---

### 3. Inference and Availability Adjustment

The system performs inference using same-day delivery volume and regional conditions, then combines the predicted total delivery time with driver availability.

```text
Predicted Total Delivery Time
+ Regional Available Time
+ Driver Schedule
+ Operational Rules
= Regional Operational MAX
```

Instead of using the raw model prediction alone, the system adjusts the result based on actual working time and driver schedules.

---

### 4. MAX Calculation

Based on the predicted total delivery time and driver schedules, the system calculates maximum deliverable volume by driver type.

```text
Regional Total Volume
→ Predicted Delivery Time
→ Capacity Calculation Based on Available Driver Time
→ MAX Distribution for Fixed / FLEX Drivers
→ Final MAX Output
```

The final output is used as the volume constraint for each driver in the clustering system.

---

### 5. Production Automation

This project was built as a daily production pipeline, not a one-off analysis script.

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
Postal Code Clustering Lambda Uses Latest MAX
```

EventBridge triggers the pipeline every day before the clustering system runs, removing the need for operators to manually calculate 기준 values.

---

### 6. Operational Output

The final MAX values are automatically updated to Google Sheets.

The operations team can use the latest MAX values immediately before clustering without writing queries or manually processing files.

![MAX Calculation Result in Google Sheets](./docs/images/image1.png)

---

## System Architecture

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
LightGBM Training / Batch Inference
        ↓
MAX Capacity Calculation
        ↓
Google Sheets API Update
        ↓
Postal Code Clustering Lambda Input
```

---

## Tech Stack

- **Python**
- Pandas / NumPy
- LightGBM
- AWS Lambda
- AWS SAM
- Lambda Container Image
- EventBridge Scheduler
- VPC / Subnet / Security Group
- MySQL / PostgreSQL
- Google Sheets API
- CloudWatch Logs

---

## Operational Output

MAX Predictor automatically reflects the calculated results in Google Sheets.

This sheet is used by the operations team as reference data before clustering, and regional, weekday, and driver-type MAX values are updated automatically.

![MAX Shipping Result](./docs/images/image1.png)

---

## Integration with the Clustering System

Delivery MAX Predictor is an upstream system for the Postal Code Clustering Lambda.

```text
Delivery MAX Predictor
        ↓
Regional / Driver-level MAX Calculation
        ↓
Google Sheets Update
        ↓
Postal Code Clustering Lambda Loads MAX Values
        ↓
Driver-level Cluster Volume Constraints
        ↓
Hub Admin App Clustering Result
```

In other words, MAX Predictor is not just a standalone model.  
It generates the key input values that determine the quality of the production clustering system.

---

## Measured Results

| Metric | Before | After | Impact |
|---|---:|---:|---|
| MAX Estimation | Manual, experience-based judgment | ML-based automated calculation | Automated operational decision-making |
| SLA | 97.15% | 97.93% | +0.78% improvement |
| Reference Data Update | Manual update | Daily automated update | Improved data freshness |
| Clustering Input | Static / experience-based values | Prediction-based MAX | Improved volume balance |
| Operations Team Workload | Manual calculation and review | Google Sheets auto-update | Reduced operational burden |

---

## Why This Is a Strong MLOps Project

This project is not just about training a model.  
It is a production MLOps case where a core operational decision metric is generated automatically by an ML system and executed daily in a real operational environment.

### Key MLOps Capabilities Demonstrated

- Built a DB-connected data pipeline using company operation data.
- Automated Feature Engineering → Training → Batch Inference.
- Built a serverless production system on AWS Lambda.
- Scheduled daily execution through EventBridge.
- Integrated Google Sheets as an operations-facing output interface.
- Connected the result to a downstream clustering system.
- Measured performance through operational KPIs.

---

## Repository Structure

```text
Max_deli_portfolio/
├── README.md
├── README_Kver.md
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

> The detailed directory structure may vary depending on the actual repository layout.

---

## Key Takeaway

This project converted driver MAX capacity estimation from an experience-based manual process into an automated ML-driven production pipeline.

By combining **LightGBM prediction**, **AWS Lambda automation**, **direct DB integration**, and **Google Sheets operational output**, the system improved SLA stability and supplied higher-quality input data to the downstream clustering system.
