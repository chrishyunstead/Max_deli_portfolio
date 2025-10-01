import pandas as pd

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from lightgbm import LGBMRegressor
import lightgbm as lgb

def process_random_forest(df_model, delivery_col='deliveries', time_col='deliveries_time', 
                    date_col='Date', sector_col='Area', day_col='day',
                    min_delivery_threshold=50, predict_df=None):
    """
    RandomForest 학습 파이프라인
    """
    # 1. 중복되는 (Date, user_id) 조합 찾기 => 같은 날 한 user_id가 두 sector를 간 경우
    duplicated_pairs = (
        df_model.groupby(['Date', 'user_id'])
        .filter(lambda x: len(x) > 1)
        .index
    )
    # 2. 해당 인덱스를 가진 row 제거
    random_forest_cleaned = df_model.drop(index=duplicated_pairs).reset_index(drop=True)
    
    df = random_forest_cleaned.copy()

    # 1. 시간 컬럼 timedelta로 변환
    df[time_col] = pd.to_timedelta(df[time_col])

    # 2. 그룹핑 및 합계
    pivot_df = df.pivot_table(
        index=[date_col, sector_col, day_col],
        values=[delivery_col, time_col],
        aggfunc={delivery_col: 'sum', time_col: 'sum'}
    ).reset_index()

    # 3. 시간(초)로 변환
    pivot_df[time_col] = pivot_df[time_col].dt.total_seconds()

    # 4. 라벨 인코딩
    sector_encoder = LabelEncoder()
    day_encoder = LabelEncoder()

    pivot_df[sector_col] = sector_encoder.fit_transform(pivot_df[sector_col])
    pivot_df[day_col] = day_encoder.fit_transform(pivot_df[day_col])

    # 5. 물량 필터링
    filtered_df = pivot_df[pivot_df[delivery_col] > min_delivery_threshold].copy()
    filtered_df['time_per_delivery'] = filtered_df[time_col] / filtered_df[delivery_col]

    # 6. 이상치 제거 1
    Q1 = filtered_df['time_per_delivery'].quantile(0.25)
    Q3 = filtered_df['time_per_delivery'].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered_df = filtered_df[(filtered_df['time_per_delivery'] >= lower) & 
                            (filtered_df['time_per_delivery'] <= upper)].drop(columns=['time_per_delivery'])
    
    # 6. 이상치 제거 2
    Q1 = filtered_df[time_col].quantile(0.25)
    Q3 = filtered_df[time_col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered_df = filtered_df[(filtered_df[time_col] >= lower) & 
                            (filtered_df[time_col] <= upper)]

    # 7. 학습
    features = filtered_df[[sector_col, day_col, delivery_col]]
    target = filtered_df[time_col]


    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    # 평균제곱오차
    rmse = mse ** 0.5
    r2 = r2_score(y_test, y_pred)

    metrics = {
        'RMSE': rmse,
        'R2': r2
    }

    # 모델 성능 디버깅
    print(f'RMSE, R2: {metrics}')

    # 8. 오늘 데이터 예측
    prediction_result = None 
    if predict_df is not None:
        pred_df = predict_df.copy()
        
        pred_df = pred_df.groupby(['Area', 'day'])['shipping_uuid'].agg('count').reset_index()
        pred_df.rename(columns={'shipping_uuid': 'deliveries'}, inplace=True)
        print(f'pred_df {pred_df}')

        pred_df = pred_df[pred_df[sector_col].isin(sector_encoder.classes_)]
        pred_df = pred_df[pred_df[day_col].isin(day_encoder.classes_)]

        pred_df[sector_col] = sector_encoder.transform(pred_df[sector_col])
        pred_df[day_col] = day_encoder.transform(pred_df[day_col])

        pred_features = pred_df[[sector_col, day_col, delivery_col]]

        print(f'pred_features: {pred_features}')

        pred_df['predicted_deliveries_time'] = model.predict(pred_features)

        # 복원
        pred_df['decoded_sector'] = sector_encoder.inverse_transform(pred_df[sector_col])
        pred_df['decoded_day'] = day_encoder.inverse_transform(pred_df[day_col])

        prediction_result = pred_df[
            ['decoded_sector', 'decoded_day', delivery_col, 'predicted_deliveries_time']
        ].rename(columns={
            'decoded_sector': 'Area',
            'decoded_day': 'day'
        })
        
        prediction_result['predicted_time_per_delivery'] = prediction_result['predicted_deliveries_time'] / prediction_result['deliveries']
    
    return prediction_result


def process_lgbm(df_model, delivery_col='deliveries', time_col='deliveries_time', 
                 date_col='Date', sector_col='Area', day_col='day',
                 min_delivery_threshold=50, predict_df=None,
                 lgbm_params=None):
    """
    LightGBM 학습 파이프라인 (기존 RandomForest 버전 대체)
    """
    # 1) 같은 날 한 user_id가 두 sector를 간 경우 제거
    duplicated_pairs = (
        df_model.groupby(['Date', 'user_id'])
        .filter(lambda x: len(x) > 1)
        .index
    )
    random_forest_cleaned = df_model.drop(index=duplicated_pairs).reset_index(drop=True)
    df = random_forest_cleaned.copy()

    # 2) 시간 컬럼 -> timedelta
    df[time_col] = pd.to_timedelta(df[time_col])

    # 3) 그룹핑 및 합계
    pivot_df = df.pivot_table(
        index=[date_col, sector_col, day_col],
        values=[delivery_col, time_col],
        aggfunc={delivery_col: 'sum', time_col: 'sum'}
    ).reset_index()

    # 4) 시간(초)로 변환
    pivot_df[time_col] = pivot_df[time_col].dt.total_seconds()

    # 5) 라벨 인코딩 (LightGBM 카테고리도 가능하지만, 기존 흐름 유지)
    sector_encoder = LabelEncoder()
    day_encoder = LabelEncoder()
    pivot_df[sector_col] = sector_encoder.fit_transform(pivot_df[sector_col])
    pivot_df[day_col]   = day_encoder.fit_transform(pivot_df[day_col])

    # 6) 물량 필터링 및 1차 이상치 제거(time_per_delivery)
    filtered_df = pivot_df[pivot_df[delivery_col] > min_delivery_threshold].copy()
    if filtered_df.empty:
        print('학습 데이터가 비어 있습니다. 필터 조건을 확인하세요.')
        return None

    filtered_df['time_per_delivery'] = filtered_df[time_col] / filtered_df[delivery_col]
    Q1 = filtered_df['time_per_delivery'].quantile(0.25)
    Q3 = filtered_df['time_per_delivery'].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered_df = filtered_df[
        (filtered_df['time_per_delivery'] >= lower) &
        (filtered_df['time_per_delivery'] <= upper)
    ].drop(columns=['time_per_delivery'])

    # 7) 2차 이상치 제거(총 시간 기준)
    Q1 = filtered_df[time_col].quantile(0.25)
    Q3 = filtered_df[time_col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered_df = filtered_df[
        (filtered_df[time_col] >= lower) &
        (filtered_df[time_col] <= upper)
    ]

    if filtered_df.empty:
        print('이상치 제거 이후 학습 데이터가 비었습니다.')
        return None
    
    filtered_df.to_csv('lgbm_training_data.csv', index=False)  # 디버깅용 저장
    print('디버깅용 학습 데이터 저장 완료: lgbm_training_data.csv')

    # 8) 학습/평가
    features = filtered_df[[sector_col, day_col, delivery_col]]
    target   = filtered_df[time_col]

    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42
    )

    # 기본 하이퍼파라미터 (필요시 lgbm_params로 덮어쓰기)
    default_params = dict(
        objective='regression',
        boosting_type='gbdt',
        n_estimators=3000,
        learning_rate=0.03,
        num_leaves=63,
        min_data_in_leaf=10,          # 데이터 적으면 좀 낮춰보기
        min_gain_to_split=0.0,        # 혹시 높게 잡혀있다면 0으로
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1
    )
    if lgbm_params:
        default_params.update(lgbm_params)

    model = LGBMRegressor(**default_params)

    # 조기 종료를 위한 검증셋 지정
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='rmse',
        callbacks=[lgb.early_stopping(100)]
        # 최신 lightgbm은 early_stopping_rounds 대신 callbacks 사용 권장이나,
        # 버전 호환 위해 필요시 다음과 같이 사용 가능:
        # early_stopping_rounds=100
    )

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5
    r2 = r2_score(y_test, y_pred)

    metrics = {'RMSE': rmse, 'R2': r2}
    print(f'RMSE, R2: {metrics}')

    # 9) 오늘 데이터 예측 (선택)
    prediction_result = None
    if predict_df is not None:
        pred_df = predict_df.copy()
        # (Area, day)별 물량 count 형태로 변환
        pred_df = pred_df.groupby(['Area', 'day'])['uuid'].agg('count').reset_index()
        pred_df.rename(columns={'uuid': 'deliveries'}, inplace=True)
        print(f'pred_df {pred_df}')

        # 학습에 등장했던 카테고리만 사용 (unseen category 방지)
        pred_df = pred_df[pred_df[sector_col].isin(sector_encoder.classes_)]
        pred_df = pred_df[pred_df[day_col].isin(day_encoder.classes_)]

        # 인코딩
        pred_df[sector_col] = sector_encoder.transform(pred_df[sector_col])
        pred_df[day_col]    = day_encoder.transform(pred_df[day_col])

        pred_features = pred_df[[sector_col, day_col, delivery_col]]
        print(f'pred_features: {pred_features}')

        # 예측
        pred_df['predicted_deliveries_time'] = model.predict(pred_features)

        # 복원
        pred_df['decoded_sector'] = sector_encoder.inverse_transform(pred_df[sector_col])
        pred_df['decoded_day']    = day_encoder.inverse_transform(pred_df[day_col])

        prediction_result = pred_df[
            ['decoded_sector', 'decoded_day', delivery_col, 'predicted_deliveries_time']
        ].rename(columns={'decoded_sector': 'Area', 'decoded_day': 'day'})

        prediction_result['predicted_time_per_delivery'] = (
            prediction_result['predicted_deliveries_time'] / prediction_result['deliveries']
        )

    return prediction_result