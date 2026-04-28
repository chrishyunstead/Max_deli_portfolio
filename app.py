import os
import json

from utils.db_handler import DBHandler
from utils.preprocess.preprocess_pred import preprocess_predict
from utils.preprocess.preprocess_available_time import process_available_delivery_time

from queries.model_dataset import ModelDatasetQuery
from queries.schedule import ScheduleDatasetQuery
from queries.time import TimeDatasetQuery
from queries.shipping import ShippingDatasetQuery


from integrations.push_spread_sheet import push_to_spreadsheet
from datetime import datetime, timedelta, timezone

from model.train import train
from model.predict import predict


def _pack_df(df, sample_n: int):
    """응답 payload 축소용: DF를 count/columns/상위 N rows로 패킹"""
    if df is None:
        return {"count": 0, "sample_n": 0, "columns": [], "data": []}
    records = df.to_dict(orient="records")
    n = len(records)
    s = min(sample_n, n)
    return {
        "count": n,
        "sample_n": s,
        "columns": list(df.columns),
        "data": records[:s],
    }


def lambda_handler(event, context):
    print(f"[lambda] Event: {event}")
    ACCOUNT_ENV = os.environ.get("ACCOUNT_ENV", "local")
    print(f"[lambda] ACCOUNT_ENV: {ACCOUNT_ENV}")

    db_handler = DBHandler()
    model_query = ModelDatasetQuery(db_handler)
    schedule_query = ScheduleDatasetQuery(db_handler)
    time_query = TimeDatasetQuery(db_handler)
    shipping_query = ShippingDatasetQuery(db_handler)

    print("[lambda] fetch_df_model begin")
    df_model = model_query.fetch_dataset_df()
    print(
        f"[lambda] fetch_df_model end rows={len(df_model)} cols={list(df_model.columns)}"
    )

    print("[lambda] fetch_df_schedule begin")
    df_schedule = schedule_query.fetch_dataset_df()
    print(
        f"[lambda] fetch_df_schedule end rows={len(df_schedule)} cols={list(df_schedule.columns)}"
    )

    print("[lambda] fetch_df_time begin")
    df_time = time_query.fetch_dataset_df()
    print(
        f"[lambda] fetch_df_time end rows={len(df_time)} cols={list(df_time.columns)}"
    )

    print("[lambda] fetch_df_shipping begin")
    df_shipping = shipping_query.fetch_dataset_df()
    print(
        f"[lambda] fetch_df_shipping end rows={len(df_shipping)} cols={list(df_shipping.columns)}"
    )

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    workflow_date = now_kst.strftime("%Y-%m-%d")
    day_str = now_kst.strftime("%A").lower()
    df_shipping["day"] = day_str

    # Train
    model, sector_encoder, day_encoder = train(df_model=df_model)

    # # Local test train
    # # model, sector_encoder, day_encoder = local_test_train(
    # #     df_model=df_model
    # # )

    # Predict
    prediction_result = predict(model, df_shipping, sector_encoder, day_encoder)

    # Available delivery time preprocessing
    available_delivery_time_no_outlier_sector = process_available_delivery_time(df_time)

    # Finalize prediction results
    merged_df = preprocess_predict(
        df_schedule,
        prediction_result,
        available_delivery_time_no_outlier_sector,
    )

    print(f"prediction_result: {prediction_result.head()}")
    print(
        f"available_delivery_time_no_outlier_sector: {available_delivery_time_no_outlier_sector.head()}"
    )
    print(f"df_schedule: {df_schedule.head()}")
    print(f"merged_df: {merged_df.head()}")

    # ✅ 로컬에서는 응답을 “짧게” (원하면 더 앞에서 early return도 가능)
    if ACCOUNT_ENV == "local":
        # 로컬에서 업로드까지 같이 테스트하고 싶으면 env로 SKIP_SHEET_UPLOAD=false 주면 됨

        try:
            push_to_spreadsheet(merged_df)
            print(f"✅ 스프레드시트 업로드 완료! rows={len(merged_df)}")
        except Exception as e:
            print(f"[ERROR] spreadsheet upload failed: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": False, "error": f"spreadsheet upload failed: {e}"},
                    ensure_ascii=False,
                ),
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "ok": True,
                    "status": 200,
                    "env": ACCOUNT_ENV,
                    "workflow_date": workflow_date,
                    "day": day_str,
                    "counts": {
                        "model": len(df_model),
                        "schedule": len(df_schedule),
                        "time": len(df_time),
                        "shipping": len(df_shipping),
                        "merged": len(merged_df),
                    },
                },
                ensure_ascii=False,
            ),
        }

    # 6) stage/prod: 시트 업로드 + (필요시) 상세 payload
    try:
        push_to_spreadsheet(merged_df)
        print(f"✅ 스프레드시트 업로드 완료! rows={len(merged_df)}")

        # ✅ 응답 크기 제한 대비: 샘플만 반환
        SAMPLE_N = int(os.environ.get("SAMPLE_N", "20"))

        payload = {
            "ok": True,
            "env": ACCOUNT_ENV,
            "workflow_date": workflow_date,
            "day": day_str,
            "model": _pack_df(df_model, SAMPLE_N),
            "schedule": _pack_df(df_schedule, SAMPLE_N),
            "time": _pack_df(df_time, SAMPLE_N),
            "shipping": _pack_df(df_shipping, SAMPLE_N),
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload, ensure_ascii=False, default=str),
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
        }
