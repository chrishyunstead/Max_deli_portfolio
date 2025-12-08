Delivery Time MAX Predictor Pipeline

본 프로젝트는 지역별 배송 물량·가용시간·기사 스케줄·예측 모델을 통합하여 실제 운영 가능한 MAX 배송량을 자동 산출하는 파이프라인입니다.
Holistics BI → 모델 학습/예측 → 가용시간 결합 → 기사 타입별 가용량 배분 → Google Sheets 반영까지 완전 자동화된 일일 계산 프로세스를 제공합니다.

전체 파이프라인은 GitHub Actions 스케줄링과 Google Sheets를 기반으로 실행됩니다.

전체 구조 (Pipeline Overview)
Holistics BI → 학습/예측용 데이터 로딩
        ↓
RandomForestRegressor 학습
        ↓
오늘 물량(deliveries)에 대한 총 소요시간 예측
        ↓
(Area, day)별 가용시간(median)과 결합
        ↓
기사 타입(Y/R/O/WHITE 등)별 가용시간 배분
        ↓
MAX 배송량 계산
        ↓
Google Spreadsheet 업데이트

디렉터리 구조
.
├─ app.py                         # 전체 파이프라인 실행 진입점
├─ sheet_data_loader.py           # Holistics BI → 데이터 로딩
├─ available_time_processing.py   # 가용시간 전처리(IQR 제거, median 집계)
├─ prediction.py                  # RandomForest 학습 및 예측
├─ preprocess_predict.py          # 가용시간 × 예측결과 × 스케줄 → MAX 산출
├─ google_sheet_api.py            # 예측 결과 Google Sheets 업로드
└─ config.py                      # 시트명, 상수 설정

사용 데이터

파이프라인은 Holistics BI에서 수집한 4종 데이터 소스로 구성됩니다.

1) 학습 데이터 — df_model (TAB_MODEL)

RandomForest 모델 학습에 사용되는 기본 데이터.

Column	설명
Area	지역 코드
day	요일(0~6)
deliveries	해당 날짜·지역의 배송 물량
deliveries_time	실제 소요된 총 배송 시간(타깃)

모델이 학습하는 함수:

f(Area, day, deliveries) → deliveries_time

2) 가용시간 데이터 — df_time (TAB_TIME)

기사별 실제 작업 가능시간을 집계한 데이터.

전처리 과정:

(date, user_id) 중복 제거

IQR 기반 이상치 제거

(area, day) 기준 median 집계

최종 스키마:

Column	설명
area	지역 코드
day	요일
available_delivery_time	중간 가용시간(median)
3) 오늘 물량 데이터 — predict_df (TAB_PREDICT)

예측 대상 날짜의 배송 물량.

Column	설명
Area	지역 코드
day	요일
deliveries	오늘 예상 물량

예측 결과 생성:

predicted_deliveries_time

predicted_time_per_delivery

4) 오늘 스케줄 데이터 — df_schedule (TAB_SCHEDULE)

기사 타입별 가용시간 배분 기준.

동작 방식:

스케줄이 존재하면 → Area + Type 기준 분배

스케줄이 없으면 → WHITE 기사 기준 단일 처리

BLUE 타입은 배분에서 제외

모델 구성
입력 피처
Feature	설명
Area	지역 코드(Label Encoding)
day	요일(Label Encoding)
deliveries	배송 물량
타깃 변수
Target	설명
deliveries_time	총 소요 시간

예측 시 생성되는 값:

predicted_deliveries_time

predicted_time_per_delivery = predicted_deliveries_time / deliveries

MAX 산출 로직

다음 로직이 preprocess_predict.py 에서 수행됩니다.

예측 결과 + 가용시간(median)
→ (Area, day) 기준 merge

스케줄 데이터와 결합하여
→ 기사 타입별 가용시간 배분

기사 타입별 MAX 계산

MAX_shipping = floor(
    available_delivery_time / predicted_time_per_delivery
)


최종적으로 Area, day, Type 조합별 실제 운영 가능한 최대 물량이 산출됩니다.

출력 형식 (Google Sheets 업로드)

업로드되는 결과 스키마 예시:

Column	설명
Area	지역 코드
day	요일
deliveries	오늘 배송 물량
available_delivery_time	median 가용시간
predicted_deliveries_time	모델 예측 총 소요시간
predicted_time_per_delivery	건당 예상 소요시간
Type	기사 타입(Y/R/O/WHITE 등)
MAX_shipping	처리 가능한 최대 물량

운영팀은 Google Sheets에서 자동 갱신된 MAX 값을 즉시 확인할 수 있습니다.

Google Sheets 연동

google_sheet_api.py는 다음을 수행합니다.

Google 서비스 계정 인증

기존 데이터 백업 또는 덮어쓰기

예측 결과 테이블을 지정 워크시트에 업로드

기술 스택

Python

pandas / numpy

scikit-learn (RandomForestRegressor)

Holistics BI API

Google Sheets API (google-auth, gspread)

GitHub Actions 스케줄링

프로젝트 특징

실제 운영 데이터 기반 예측 파이프라인

가용시간 × 예측시간 × 스케줄을 결합한 현실적 MAX 계산

Holistics BI → GitHub Actions → Google Sheets까지 완전 자동화

SLA 준수 및 배차 결정 지원을 위한 정량적 운용 근거 제공