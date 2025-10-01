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
from local_test_data_import import AutoContainerGeneration
model_proc = AutoContainerGeneration(version=2, debug=True)


# db_handler = DBHandler()
# schedule_processor = ScheduleProcessor(db_handler)
# shipping_processor = ShippingProcessor(db_handler)
# model_processor = ModelProcessor(db_handler)
# time_processor = TimeProcessor(db_handler)

workflow_date = datetime.today().strftime("%Y-%m-%d")
# workflow_date = '2025-09-28'  # 고정값 테스트

# df_model = model_processor.fetch_model(workflow_date)
# df_time = time_processor.fetch_time(workflow_date)
# df_schedule = schedule_processor.fetch_schedules(workflow_date)
# predict_df = shipping_processor.fetch_shipping(workflow_date)

# 로컬 테스트
df_model, df_time, predict_df, df_schedule = model_proc.fetch_all_data()
# df_model.to_csv('df_model.csv', index=False)
# df_time.to_csv('df_time.csv', index=False) 
# predict_df = pd.read_csv('20250928_df.csv')
# df_schedule = pd.read_csv('20250928_schedule.csv')

day_str = datetime.strptime(workflow_date, "%Y-%m-%d").strftime('%A').lower()

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