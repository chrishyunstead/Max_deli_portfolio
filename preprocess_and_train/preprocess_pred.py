import pandas as pd
import numpy as np

def preprocess_predict(df_schedule, prediction_result, available_delivery_time_no_outlier_sector):
        """
        스케줄(df_schedule)이 없거나 비어도 깨지지 않도록 방어.
        - 스케줄이 있으면: Area+Type 기준으로 BLUE 제외 후 merge
        - 스케줄이 없으면: 전부 WHITE로 통일하고 Area 기준으로만 merge
        반환 컬럼 스키마는 유지.
        """
        prediction_result.rename(columns={'area': 'Area'}, inplace=True)
        available_delivery_time_no_outlier_sector.rename(columns={'area': 'Area'}, inplace=True)

        # 출력 스키마 고정
        out_cols = [
            'Area', 'day', 'deliveries',
            'predicted_time_per_delivery', 'available_delivery_time',
            'MAX_shipping'
        ]

        # 예측값 자체가 없으면 바로 빈 프레임 반환
        if prediction_result is None or prediction_result.empty:
            return pd.DataFrame(columns=out_cols)

        pred = prediction_result.copy()

        # 잔여시간 DF 준비
        avail = available_delivery_time_no_outlier_sector.copy()
        if 'available_delivery_time' in avail.columns:
            avail['available_delivery_time'] = pd.to_numeric(
                avail['available_delivery_time'], errors='coerce'
            )

        has_schedule = isinstance(df_schedule, pd.DataFrame) and (not df_schedule.empty)

        if has_schedule:

            blue_areas = df_schedule.loc[df_schedule["Type"] == "BLUE", "Area"].unique().tolist()
            print(f'BLUE 지역 {blue_areas}')
            pred = pred[~(pred["Area"].isin(blue_areas))].reset_index(drop=True)
            print(f'[pred] BLUE 지역 제외: {pred}')
            avail = avail[~(avail["Area"].isin(blue_areas))].reset_index(drop=True)
            print(f'[avail] BLUE 지역 제외: {avail}')

        merged = pred.merge(
            avail[['Area', 'available_delivery_time']],
            on=['Area'], how='left'
        )
        
        merged['available_delivery_time'] = pd.to_numeric(
            merged['available_delivery_time'], errors='coerce'
        ).fillna(0)      # ← NaN 이면 0으로 대체

        # MAX_shipping 계산 (0/NaN/Inf 방어 + 정수화)
        merged['predicted_time_per_delivery'] = pd.to_numeric(
            merged['predicted_time_per_delivery'], errors='coerce'
        ).replace(0, np.nan)

        merged['MAX_shipping'] = np.floor(
            merged['available_delivery_time'] / merged['predicted_time_per_delivery']
        ).replace([np.inf, -np.inf], 0).fillna(0).astype(int)

        # 누락 컬럼 보완 및 컬럼 순서 정리
        for c in out_cols:
            if c not in merged.columns:
                merged[c] = (0 if c == 'MAX_shipping' else np.nan)

        return merged[out_cols]