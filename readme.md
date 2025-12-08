Max Deliveries Prediction

지역별·요일별 배송 물량 대비 최대 처리 가능량(MAX)을 예측하는 프로덕션 모델 파이프라인

이 프로젝트는 실배송 데이터를 기반으로
(Area, day, deliveries) → 총 배송 소요시간(deliveries_time) 관계를 학습하고,
이를 바탕으로 운영 현장에서 사용할 수 있는
기사 타입별 최대 처리 물량(MAX) 을 자동 산출하는 예측 시스템이다.

학습·예측 데이터는 Holistics BI에서 API로 적재되며,
결과는 Google Spreadsheet로 전송되어 운영팀이 즉시 활용할 수 있는 형태로 제공된다.

전체 구조
Holistics BI → 데이터 로딩
      ↓
RandomForestRegressor 학습
      ↓
오늘 물량(deliveries) 예측
      ↓
(Area, day)별 가용시간과 결합
      ↓
기사 타입별 가용시간 배분
      ↓
MAX 물량 계산
      ↓
Google Spreadsheet 업데이트

디렉터리 구조
.
├─ app.py                     # 전체 파이프라인 실행 흐름
├─ sheet_data_loader.py       # Holistics BI → Google Sheets 데이터 로더
├─ available_time_processing.py  # 가용시간 전처리(IQR 제거, median 집계)
├─ prediction.py              # 학습 및 예측(RandomForest)
├─ preprocess_predict.py      # 가용시간 × 예측결과 × 스케줄 → MAX 산출
├─ google_sheet_api.py        # 예측 결과 Google Sheet 업로드
└─ config.py                  # 시트명/상수 설정

데이터 구성 (실제 코드 기반)

모델과 MAX 산출에 사용되는 데이터는 총 네 가지이며, 모두 Holistics에서 적재된다.

1) 학습 데이터(df_model) — TAB_MODEL

랜덤포레스트 학습에 사용.

Column	Description
Area	지역 코드
day	요일
deliveries	해당 날짜·지역 배송 물량
deliveries_time	실제 총 배송 시간

→ 모델이 학습하는 함수
f(Area, day, deliveries) → deliveries_time

2) 가용시간 데이터(df_time) — TAB_TIME

매일 기사들의 실제 작업 가능 시간을 모아 생성.

전처리 단계:

(date, user_id) 중복 제거

available_delivery_time 이상치 제거(IQR)

(area, day) 단위로 median 집계 → 운영 안정성 확보

최종 스키마:

| area | day | available_delivery_time(median) |

3) 오늘 물량 데이터(predict_df) — TAB_PREDICT

예측 대상 날짜의 물량.

| Area | day | deliveries |

이 값이 모델 입력으로 들어가
→ predicted_deliveries_time
→ predicted_time_per_delivery
이 계산된다.

4) 오늘 스케줄 데이터(df_schedule) — TAB_SCHEDULE

기사 타입별(예: Y, R, O, WHITE 등) 작업 가능량 비율 제공.

역할:

스케줄 존재 → Area + Type 기준으로 가용시간 분배

스케줄 없음 → White 기사 기준으로 통합 처리

결과적으로 타입별 MAX 계산이 가능해진다.

핵심 로직
1. 학습(RandomForestRegressor)

사용 Feature는 오직 세 가지:

Feature	설명
Area (LabelEncoded)	지역 특성 반영
day (LabelEncoded)	요일 특성 반영
deliveries	배송 물량

Target:

Target	설명
deliveries_time	실제 소요된 총 배송 시간

예측 결과는:

predicted_deliveries_time

predicted_time_per_delivery (건당 예상 소요시간)

으로 변환된다.

이 단순한 구조가 실제 운영 맥락(물량·지역·요일) 을 가장 직접적으로 반영한다.

2. 가용시간 결합 & 기사 타입별 배분

preprocess_predict.py 내부 로직에 따라:

(Area, day) 기준으로 predicted_time_per_delivery 결합

스케줄(df_schedule)과 merge

BLUE 제외

스케줄 없으면 WHITE 기반으로 처리

타입별 가용시간 계산

3. 최종 MAX 계산
MAX_shipping = floor(
    available_delivery_time / predicted_time_per_delivery
)


즉,

"해당 지역·요일·기사 타입이 처리할 수 있는 최대 배송량"

을 완전 자동으로 산출한다.

출력 구조

최종적으로 Google Sheet에 업로드되는 컬럼:

| Area | day | deliveries | available_delivery_time | predicted_deliveries_time | predicted_time_per_delivery | Type | MAX_shipping |

운영팀은 이를 기반으로 기사 배정 및 작업 계획을 수립한다.

Google Sheets 연동

google_sheet_api.py 에서 다음 수행:

기존 기록 백업

MAX 예측 결과 업로드

특정 시트 Range에 자동 반영

Holistics → Python → Google Sheets 로 이어지는
완전 자동화된 운영 파이프라인이다.

기술 스택

Python

pandas

scikit-learn (RandomForest)

numpy

Google API

google-auth

gspread

Holistics BI API

Scheduling

외부 Cron API (매일 12:30 자동 실행)

프로젝트 특징

실제 운영 데이터 기반 학습 및 예측

가용시간 + 스케줄 + 예측 결과의 통합 처리

기사 타입별 실사용 가능한 MAX 자동 산출

Google Sheet 통한 운영팀 즉시 활용 가능

전량 자동화된 파이프라인