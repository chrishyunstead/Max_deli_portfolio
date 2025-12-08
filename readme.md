# Delivery Time MAX Predictor Pipeline

본 프로젝트는 지역별 배송 물량·가용시간·기사 스케줄·예측 모델을 통합하여 실제 운영 가능한 MAX 배송량을 자동 산출하는 엔진입니다.
Holistics BI → 모델 학습/예측 → 가용시간 결합 → 기사 타입별 용량 계산 → Google Sheets 업데이트까지
완전 자동화된 일일 운영 파이프라인을 제공합니다.

전체 파이프라인은 GitHub Actions 스케줄링과 Google Sheets API 기반으로 실행됩니다.

## 아키텍처 개요

```text
GitHub Actions (Scheduler)
↓
데이터 로딩 (Holistics BI)

모델 학습용 데이터

가용시간 데이터

오늘 물량 데이터

기사 스케줄 데이터
↓
RandomForestRegressor 학습
↓
오늘 물량 → 총 소요시간 예측
↓
(Area, day)별 median 가용시간과 결합
↓
기사 타입(Y/R/O/WHITE)별 가용시간 배분
↓
MAX 배송 가능 건수 계산
↓
Google Sheets 자동 업데이트
```

## 디렉터리 구조

```text
.
├─ app.py # 전체 파이프라인 실행 진입점
├─ sheet_data_loader.py # Holistics BI → 데이터 로딩
├─ available_time_processing.py # 가용시간 전처리(IQR 제거, median 집계)
├─ prediction.py # RandomForest 학습 및 예측
├─ preprocess_predict.py # 가용시간 × 예측결과 × 스케줄 → MAX 산출
├─ google_sheet_api.py # Google Sheets 업로드 모듈
└─ config.py # 시트명 및 프로젝트 상수 설정
```

## 핵심 로직

### 1. 모델 학습 및 소요시간 예측

```text

입력 피처:
• Area
• day
• deliveries

타깃:
• deliveries_time

RandomForestRegressor 학습

예측:
• predicted_deliveries_time
• predicted_time_per_delivery
```

### 2. 가용시간 처리

```text

(date, user_id) 중복 제거

IQR 기반 이상치 제거

(area, day) median 집계
```

### 3. MAX 배송량 산출

```text
MAX_shipping = floor(
available_delivery_time / predicted_time_per_delivery
)
```

## 출력 예시

```text
Area day Type deliveries available_time pred_time_per_deliv MAX_shipping
S01 2 WHITE 412 285 3.41 83
S01 2 Y 412 120 3.41 35
S01 2 O 412 90 3.41 26
```

## 기술 스택

```text
Python : pandas, numpy, scikit-learn
Data Source : Holistics BI API
Output : Google Sheets API
Scheduler : GitHub Actions
```