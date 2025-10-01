from preprocess_and_train.train_pred_model import process_random_forest, process_lgbm
from preprocess_and_train.preprocess_available_delivery_time import process_available_delivery_time
# from data.schedule_data import ScheduleProcessor
# from data.db_handler import DBHandler
# from data.shipping_data import ShippingProcessor
from preprocess_and_train.preprocess_pred import preprocess_predict
# from data.model_data import ModelProcessor
# from data.time_data import TimeProcessor

# 스프레드 시트로 데이터프레임 쏘기
from preprocess_spread_sheet.push_spread_sheet import push_to_spreadsheet

from datetime import datetime
import pandas as pd
# 로컬 테스트
# from local_test_data_import import AutoContainerGeneration
# model_proc = AutoContainerGeneration(version=2, debug=True)

# from data_import_sheets import SheetDataLoader
# loader = SheetDataLoader()
# db_handler = DBHandler()
# schedule_processor = ScheduleProcessor(db_handler)
# shipping_processor = ShippingProcessor(db_handler)
# model_processor = ModelProcessor(db_handler)
# time_processor = TimeProcessor(db_handler)


# workflow_date = '2025-09-28'  # 고정값 테스트

# df_model = model_processor.fetch_model(workflow_date)
# df_time = time_processor.fetch_time(workflow_date)
# df_schedule = schedule_processor.fetch_schedules(workflow_date)
# predict_df = shipping_processor.fetch_shipping(workflow_date)

# 로컬 테스트
# df_model, df_time, predict_df, df_schedule = loader.fetch_all_data()
# df_model.to_csv('df_model.csv', index=False)
# df_time.to_csv('df_time.csv', index=False) 
# predict_df = pd.read_csv('20250928_df.csv')
# df_schedule = pd.read_csv('20250928_schedule.csv')

import os, time, io, requests


BASE = "https://secure.holistics.io/api/v2"
API_KEY = os.environ["HOLISTICS_API_KEY"]
HEADERS = {"X-Holistics-Key": API_KEY, "Content-Type": "application/json"}

def run_report_get_csv_url(report_id: str, poll_sec: int = 5, timeout_sec: int = 900):
    r = requests.post(f"{BASE}/report_jobs", headers=HEADERS, json={"report_id": report_id})
    r.raise_for_status()
    job_id = r.json()["data"]["id"]
    start = time.time()
    while True:
        jr = requests.get(f"{BASE}/report_jobs/{job_id}", headers=HEADERS)
        jr.raise_for_status()
        status = jr.json()["data"]["status"]
        if status == "completed":
            return jr.json()["data"]["download_url"]
        if status in ("failed", "error"):
            raise RuntimeError(f"Holistics job {job_id} failed")
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"Holistics job {job_id} timeout")
        time.sleep(poll_sec)

def fetch_report_df(report_id: str) -> pd.DataFrame:
    url = run_report_get_csv_url(report_id)
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    buf = io.BytesIO(resp.content)
    try:
        return pd.read_csv(buf)
    except:
        buf.seek(0)
        return pd.read_csv(buf, compression="gzip")

def fetch_all_from_holistics():
    report_ids = [s.strip() for s in os.environ["HOLISTICS_REPORT_IDS"].split(",")]
    if len(report_ids) != 4:
        raise RuntimeError(f"리포트 ID가 4개 필요합니다: {report_ids}")
    print("➡️ Fetching 4 Holistics reports:", report_ids)

    df_time    = fetch_report_df(report_ids[0])
    df_model     = fetch_report_df(report_ids[1])
    df_schedule  = fetch_report_df(report_ids[2])
    predict_df = fetch_report_df(report_ids[3])

    return df_time, df_model, df_schedule, predict_df

workflow_date = datetime.today().strftime("%Y-%m-%d")

day_str = datetime.strptime(workflow_date, "%Y-%m-%d").strftime('%A').lower()
df_time, df_model, df_schedule, predict_df = fetch_all_from_holistics()
# day 컬럼 추가
predict_df['day'] = day_str

# 랜덤포레스트 모델 학습
# prediction_result = process_random_forest(df_model = df_model, predict_df = predict_df)

# lightGBM 모델 학습
prediction_result = process_lgbm(df_model = df_model, predict_df = predict_df)

# available_delivery_time 구하기
available_delivery_time_no_outlier_sector = process_available_delivery_time(df_time)

# 출력 테스트 
print("RandomForest 모델:", prediction_result)

print("섹터별 평균 available_delivery_time:")
print(available_delivery_time_no_outlier_sector)


merged_df = preprocess_predict(df_schedule, prediction_result, available_delivery_time_no_outlier_sector)

print("최종 병합 결과:")
print(merged_df)

push_to_spreadsheet(merged_df)
print('스프레드 시트에 업로드 완료!')  # 시트 이름 지정