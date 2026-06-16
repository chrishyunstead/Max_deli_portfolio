# Delivus Delivery MAX Predictor

## 물량·지역·요일 기반 지역별 최대 배송량(MAX) 예측 Production MLOps 시스템

회사 DB의 배송 운영 데이터를 기반으로 지역·요일·물량별 총 배송 소요시간을 예측하고, 기사 스케줄과 지역별 가용시간을 결합하여 **운영 가능한 최대 배송량(MAX)** 을 자동 산출하는 시스템입니다.  
산출된 MAX 값은 Postalcode Clustering Lambda의 upstream 입력값으로 사용되어 기사별 과배차/저배차를 줄이고 당일배송 SLA 안정성을 높입니다.

---

## Executive Impact

| Metric | Before | After | Impact |
|---|---:|---:|---|
| MAX 산정 방식 | 경험 기반 수동 판단 | ML 기반 자동 산출 | 운영 의사결정 자동화 |
| SLA | 97.15% | 97.93% | **+0.78% 개선** |
| 기준값 업데이트 | 수동 | 일일 자동 업데이트 | 최신성 확보 |
| 클러스터링 입력값 | 고정/경험값 | 예측 기반 MAX | 물량 균형 개선 |
| 운영팀 작업 | 수작업 계산·확인 | Google Sheets 자동 반영 | 업무 부담 감소 |

---

## Business Problem

당일배송 운영에서는 기사별로 “하루에 몇 개까지 배송 가능한가”를 정확히 판단하는 것이 중요합니다.

- MAX 값이 과도하게 높으면 특정 기사에게 물량이 몰려 배송 지연이 발생합니다.
- MAX 값이 낮으면 기사 리소스를 충분히 활용하지 못해 운영 효율이 떨어집니다.
- 지역별 배송 난이도, 요일별 물량 패턴, 고정/FLEX 기사 스케줄을 동시에 반영하기 어렵습니다.
- 클러스터링 직전 최신 물량 기준값을 매번 수동으로 계산하는 데 한계가 있었습니다.

따라서 MAX 산정은 단순 참고 지표가 아니라, **클러스터링 품질과 SLA 안정성을 결정하는 핵심 운영 파라미터**였습니다.

---

## My Role

데이터 로딩부터 모델 학습, 추론, 운영 반영까지 End-to-End로 구현했습니다.

- Lambda VPC 설정을 통한 회사 DB 직접 연동 구조 구성
- 학습/추론용 운영 데이터셋 설계 및 전처리
- 지역·요일·물량 기반 총 배송 소요시간 예측 모델 개발
- LightGBM 기반 batch inference 파이프라인 구현
- 예측값과 기사 가용시간을 결합한 MAX 산출 로직 설계
- 고정 기사/FLEX 기사별 MAX 분배 로직 구현
- AWS SAM Image 기반 Lambda 배포
- EventBridge 스케줄러 기반 일일 자동 실행 구성
- Google Sheets API 연동으로 운영팀 사용 화면 자동 업데이트
- 산출 결과를 Postalcode Clustering Lambda의 upstream 데이터로 연결

---

## Core Process

### 1. DB Direct Integration

Lambda `template.yaml`에 VPC Subnet / Security Group 설정을 적용하여 회사 내부 DB에 접근할 수 있도록 구성했습니다.

```text
AWS Lambda
  → VPC Subnet / Security Group
  → Company DB
  → Historical Operation Data Load
```

### 2. Feature Engineering

운영 데이터를 모델 학습에 필요한 형태로 전처리합니다.

| Feature | Description |
|---|---|
| Area | 배송 권역 |
| Weekday | 요일별 물량·생산성 패턴 |
| Volume | 지역별 배송 아이템 수 |
| Driver Schedule | 고정 기사/FLEX 기사 가용 여부 |
| Total Delivery Time | 모델이 예측할 target |

### 3. Model Training / Inference

LightGBM 기반 회귀 모델을 사용하여 지역·요일·물량 조건에 따른 총 배송 소요시간을 예측합니다.

### 4. MAX Calculation

예측된 총 배송 소요시간과 기사 가용시간을 결합하여 운영 가능한 최대 배송량을 계산합니다.

```text
지역별 총 물량
→ 예측 배송 소요시간
→ 기사 가용시간 대비 처리 가능량 계산
→ 고정 기사 / FLEX 기사별 MAX 분배
→ 최종 MAX 산출
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

### 6. Operation Output

운영팀은 Google Sheets에서 클러스터링 직전 최신 MAX 기준값을 확인하고 활용합니다.

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
| Infra | AWS Lambda, AWS SAM, Docker Image |
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

- 회사 DB 직접 연동 기반 데이터 파이프라인 구축
- Feature Engineering → Batch Inference → 운영 지표 반영 자동화
- 서버리스 ML 시스템을 실제 운영 의사결정에 연결
- Downstream 클러스터링 시스템과 연동
- KPI 기반 성과 측정 및 지속 개선

---

## Security / Redaction

포트폴리오 공개를 위해 다음 항목은 제거하거나 샘플 값으로 대체했습니다.

- 실제 DB 접속 정보
- 실제 AWS Account ID / VPC 정보
- 실제 Google Sheets ID
- 내부 테이블명 일부
- 배포용 `samconfig.toml`

---

## Key Takeaway

> 운영팀이 경험적으로 판단하던 기사별 최대 배송량(MAX)을 ML 예측 모델과 AWS 자동화 파이프라인으로 전환하여,  
> 실제 SLA 개선과 클러스터링 품질 향상을 만든 Production MLOps 프로젝트입니다.
