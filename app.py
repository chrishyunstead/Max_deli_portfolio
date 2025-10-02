# from preprocess_and_train.train_pred_model import process_random_forest, process_lgbm
# from preprocess_and_train.preprocess_available_delivery_time import process_available_delivery_time
# # from data.schedule_data import ScheduleProcessor
# # from data.db_handler import DBHandler
# # from data.shipping_data import ShippingProcessor
# from preprocess_and_train.preprocess_pred import preprocess_predict
# # from data.model_data import ModelProcessor
# # from data.time_data import TimeProcessor

# # 스프레드 시트로 데이터프레임 쏘기
# from preprocess_spread_sheet.push_spread_sheet import push_to_spreadsheet

# from datetime import datetime
# import pandas as pd
# # 로컬 테스트
# # from local_test_data_import import AutoContainerGeneration
# # model_proc = AutoContainerGeneration(version=2, debug=True)

# # from data_import_sheets import SheetDataLoader
# # loader = SheetDataLoader()
# # db_handler = DBHandler()
# # schedule_processor = ScheduleProcessor(db_handler)
# # shipping_processor = ShippingProcessor(db_handler)
# # model_processor = ModelProcessor(db_handler)
# # time_processor = TimeProcessor(db_handler)


# # workflow_date = '2025-09-28'  # 고정값 테스트

# # df_model = model_processor.fetch_model(workflow_date)
# # df_time = time_processor.fetch_time(workflow_date)
# # df_schedule = schedule_processor.fetch_schedules(workflow_date)
# # predict_df = shipping_processor.fetch_shipping(workflow_date)

# # 로컬 테스트
# # df_model, df_time, predict_df, df_schedule = loader.fetch_all_data()
# # df_model.to_csv('df_model.csv', index=False)
# # df_time.to_csv('df_time.csv', index=False) 
# # predict_df = pd.read_csv('20250928_df.csv')
# # df_schedule = pd.read_csv('20250928_schedule.csv')

# import os, time, io, requests


# BASE = "https://secure.holistics.io/api/v2"
# API_KEY = os.environ["HOLISTICS_API_KEY"]
# HEADERS = {"X-Holistics-Key": API_KEY, "Content-Type": "application/json"}

# def run_report_get_csv_url(report_id: str, poll_sec: int = 5, timeout_sec: int = 900):
#     r = requests.post(f"{BASE}/report_jobs", headers=HEADERS, json={"report_id": int(report_id)})
#     r.raise_for_status()
#     job_id = r.json()["data"]["id"]
#     print(f"📌 Holistics job started: {job_id}")
#     start = time.time()

#     while True:
#         jr = requests.get(f"{BASE}/report_jobs/{job_id}", headers=HEADERS)
#         jr.raise_for_status()
#         data = jr.json()["data"]
#         if data["status"] == "completed":
#             print("✅ Holistics job completed")
#             return data["download_url"]
#         if data["status"] in ("failed", "error"):
#             raise RuntimeError(f"Holistics job failed: {data}")
#         if time.time() - start > timeout_sec:
#             raise TimeoutError(f"Holistics job timeout after {timeout_sec}s")
#         time.sleep(poll_sec)

# def fetch_report_df(report_id: str) -> pd.DataFrame:
#     url = run_report_get_csv_url(report_id)
#     resp = requests.get(url, stream=True)
#     resp.raise_for_status()
#     buf = io.BytesIO(resp.content)
#     try:
#         return pd.read_csv(buf)
#     except:
#         buf.seek(0)
#         return pd.read_csv(buf, compression="gzip")

# def fetch_all_from_holistics():
#     report_ids = [s.strip() for s in os.environ["HOLISTICS_REPORT_IDS"].split(",")]
#     if len(report_ids) != 4:
#         raise RuntimeError(f"리포트 ID가 4개 필요합니다: {report_ids}")
#     print("➡️ Fetching 4 Holistics reports:", report_ids)

#     df_time    = fetch_report_df(report_ids[0])
#     df_model     = fetch_report_df(report_ids[1])
#     df_schedule  = fetch_report_df(report_ids[2])
#     predict_df = fetch_report_df(report_ids[3])

#     return df_time, df_model, df_schedule, predict_df

# workflow_date = datetime.today().strftime("%Y-%m-%d")

# day_str = datetime.strptime(workflow_date, "%Y-%m-%d").strftime('%A').lower()
# df_time, df_model, df_schedule, predict_df = fetch_all_from_holistics()
# # day 컬럼 추가
# predict_df['day'] = day_str

# # 랜덤포레스트 모델 학습
# # prediction_result = process_random_forest(df_model = df_model, predict_df = predict_df)

# # lightGBM 모델 학습
# prediction_result = process_lgbm(df_model = df_model, predict_df = predict_df)

# # available_delivery_time 구하기
# available_delivery_time_no_outlier_sector = process_available_delivery_time(df_time)

# # 출력 테스트 
# print("RandomForest 모델:", prediction_result)

# print("섹터별 평균 available_delivery_time:")
# print(available_delivery_time_no_outlier_sector)


# merged_df = preprocess_predict(df_schedule, prediction_result, available_delivery_time_no_outlier_sector)

# print("최종 병합 결과:")
# print(merged_df)

# push_to_spreadsheet(merged_df)
# print('스프레드 시트에 업로드 완료!')  # 시트 이름 지정




# app.py
import os, io, time, sys, requests
import pandas as pd

# === 콘솔 인코딩 (윈도우/액션스 안전) ===
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# === 프로젝트 로직 ===
from preprocess_and_train.train_pred_model import process_lgbm  # process_random_forest 미사용
from preprocess_and_train.preprocess_available_delivery_time import process_available_delivery_time
from preprocess_and_train.preprocess_pred import preprocess_predict
from preprocess_spread_sheet.push_spread_sheet import push_to_spreadsheet

# ============== Holistics Widget Export API ==============
# 리전(APAC) 기준. EU/US면 eu/us.holistics.io로 교체
BASE = os.environ.get("HOLISTICS_BASE_URL", "https://secure.holistics.io/api/v2")
API_KEY = os.environ["HOLISTICS_API_KEY"]
# WORKSPACE_ID = os.environ.get("HOLISTICS_WORKSPACE_ID")  # 없으면 생략 가능
# DASHBOARD_ID = int(os.environ.get("HOLISTICS_DASHBOARD_ID", "0"))  # 위젯 export엔 필수는 아님

HEADERS = {
    "X-Holistics-Key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}
# if WORKSPACE_ID:
#     HEADERS["X-Holistics-Workspace-Id"] = str(WORKSPACE_ID)

def start_widget_export(widget_id: int, output: str = "csv") -> str:
    """대시보드 위젯 Export Job 시작 -> job_id 리턴"""
    # 주: widget export는 dashboard_id 없이도 submit 가능. (필터 프리셋 쓰면 필요)
    url = f"{BASE}/dashboard_widgets/{widget_id}/submit_export"
    body = {"output": output}
    r = requests.post(url, headers=HEADERS, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    job = data.get("job") or data.get("data") or data
    job_id = job["id"]
    print(f"📌 widget {widget_id} export started: job={job_id}")
    return str(job_id)

def poll_job(job_id: str, poll_sec: int = 5, timeout_sec: int = 1800) -> None:
    """Job 완료까지 대기 (status: success)"""
    url = f"{BASE}/jobs/{job_id}"
    start = time.time()
    while True:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()
        job = data.get("job") or data.get("data") or data
        status = job.get("status")
        print(f"⏳ job {job_id} status: {status}")
        if status == "success":
            return
        if status in ("failed", "error"):
            raise RuntimeError(f"Holistics job failed: {data}")
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"Holistics job timeout after {timeout_sec}s (job={job_id})")
        time.sleep(poll_sec)

def download_export(job_id: str) -> bytes:
    """완료된 Job의 결과 파일 다운로드(bytes)"""
    url = f"{BASE}/exports/download"
    r = requests.get(url, headers=HEADERS, params={"job_id": job_id}, allow_redirects=True, timeout=300)
    r.raise_for_status()
    return r.content  # CSV or GZ CSV

def fetch_widget_df(widget_id: int) -> pd.DataFrame:
    job = start_widget_export(widget_id, output="csv")
    poll_job(job)
    blob = download_export(job)
    buf = io.BytesIO(blob)
    try:
        return pd.read_csv(buf)
    except Exception:
        buf.seek(0)
        return pd.read_csv(buf, compression="gzip")

def fetch_all_from_holistics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    HOLISTICS_WIDGET_IDS: 콤마로 4개 (df_model, df_time, predict_df, df_schedule 순)
    예: "656368,656369,656370,656371"
    """
    ids = [s.strip() for s in os.environ["HOLISTICS_WIDGET_IDS"].split(",") if s.strip()]
    if len(ids) != 4:
        raise RuntimeError(f"HOLISTICS_WIDGET_IDS must have 4 comma-separated widget IDs, got: {ids}")
    widget_ids = list(map(int, ids))
    print("➡️ Fetching 4 widgets:", widget_ids)

    df_model    = fetch_widget_df(widget_ids[0])
    df_time     = fetch_widget_df(widget_ids[1])
    predict_df  = fetch_widget_df(widget_ids[2])
    df_schedule = fetch_widget_df(widget_ids[3])
    return df_model, df_time, predict_df, df_schedule

# ================== Pipeline ==================
from datetime import datetime

if __name__ == "__main__":
    workflow_date = datetime.today().strftime("%Y-%m-%d")
    day_str = datetime.strptime(workflow_date, "%Y-%m-%d").strftime("%A").lower()

    # 1) Holistics에서 4개 DF 가져오기
    df_model, df_time, predict_df, df_schedule = fetch_all_from_holistics()
    # 2) predict_df에 day 컬럼 세팅(있으면 덮어씀)
    predict_df["day"] = day_str

    # 3) LightGBM 예측
    prediction_result = process_lgbm(df_model=df_model, predict_df=predict_df)

    # 4) available_delivery_time 전처리
    available_delivery_time_no_outlier_sector = process_available_delivery_time(df_time)

    # 5) 병합
    merged_df = preprocess_predict(df_schedule, prediction_result, available_delivery_time_no_outlier_sector)

    # 6) 시트 업로드 (push_spread_sheet.py가 SHEET_ID/WORKSHEET를 읽음)
    push_to_spreadsheet(merged_df)
    print(f"✅ 스프레드시트 업로드 완료! rows={len(merged_df)}")
