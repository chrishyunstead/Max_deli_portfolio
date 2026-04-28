import pandas as pd

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# SAM 로컬테스트시, 주석 처리
from lightgbm import LGBMRegressor
import lightgbm as lgb

# local_test시 RandomForestRegressor 사용
# from sklearn.ensemble import RandomForestRegressor

# def local_test_train(df_model, delivery_col='deliveries', time_col='deliveries_time',
#                 date_col='Date', sector_col='Area', day_col='day',
#                 min_delivery_threshold=50, lgbm_params=None):

#     duplicated_pairs = (
#         df_model.groupby([date_col, 'user_id'])
#         .filter(lambda x: len(x) > 1)
#         .index
#     )
#     df = df_model.drop(index=duplicated_pairs).reset_index(drop=True)
#     df[time_col] = pd.to_timedelta(df[time_col])

#     pivot_df = df.pivot_table(
#         index=[date_col, sector_col, day_col],
#         values=[delivery_col, time_col],
#         aggfunc={delivery_col: 'sum', time_col: 'sum'}
#     ).reset_index()

#     pivot_df[time_col] = pivot_df[time_col].dt.total_seconds()

#     sector_encoder = LabelEncoder()
#     day_encoder = LabelEncoder()

#     pivot_df[sector_col] = sector_encoder.fit_transform(pivot_df[sector_col])
#     pivot_df[day_col] = day_encoder.fit_transform(pivot_df[day_col])

#     filtered_df = pivot_df[pivot_df[delivery_col] > min_delivery_threshold].copy()
#     filtered_df['time_per_delivery'] = filtered_df[time_col] / filtered_df[delivery_col]

#     Q1 = filtered_df['time_per_delivery'].quantile(0.25)
#     Q3 = filtered_df['time_per_delivery'].quantile(0.75)
#     IQR = Q3 - Q1
#     lower, upper = Q1 - 1.5*IQR, Q3 + 1.5*IQR
#     filtered_df = filtered_df[
#         (filtered_df['time_per_delivery'] >= lower) &
#         (filtered_df['time_per_delivery'] <= upper)
#     ].drop(columns=['time_per_delivery'])

#     # 2차 이상치 제거(총 시간 기준)
#     Q1 = filtered_df[time_col].quantile(0.25)
#     Q3 = filtered_df[time_col].quantile(0.75)
#     IQR = Q3 - Q1
#     lower = Q1 - 1.5 * IQR
#     upper = Q3 + 1.5 * IQR
#     filtered_df = filtered_df[
#         (filtered_df[time_col] >= lower) &
#         (filtered_df[time_col] <= upper)
#     ]

#     if filtered_df.empty:
#         print('이상치 제거 이후 학습 데이터가 비었습니다.')
#         return None

#     features = filtered_df[[sector_col, day_col, delivery_col]]
#     target = filtered_df[time_col]

#     X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

#     model = RandomForestRegressor(n_estimators=100, random_state=42)
#     model.fit(X_train, y_train)

#     y_pred = model.predict(X_test)
#     print(f"테스트 데이터 셋 RMSE: {mean_squared_error(y_test, y_pred) ** 0.5:.3f}, "
#           f"테스트 데이터셋 R2: {r2_score(y_test, y_pred):.3f}")

#     return model, sector_encoder, day_encoder


def train(
    df_model,
    delivery_col="deliveries",
    time_col="deliveries_time",
    date_col="Date",
    sector_col="Area",
    day_col="day",
    min_delivery_threshold=50,
    lgbm_params=None,
):

    duplicated_pairs = (
        df_model.groupby([date_col, "user_id"]).filter(lambda x: len(x) > 1).index
    )
    df = df_model.drop(index=duplicated_pairs).reset_index(drop=True)
    df[time_col] = pd.to_timedelta(df[time_col])

    pivot_df = df.pivot_table(
        index=[date_col, sector_col, day_col],
        values=[delivery_col, time_col],
        aggfunc={delivery_col: "sum", time_col: "sum"},
    ).reset_index()
    pivot_df[time_col] = pivot_df[time_col].dt.total_seconds()

    sector_encoder = LabelEncoder()
    day_encoder = LabelEncoder()
    pivot_df[sector_col] = sector_encoder.fit_transform(pivot_df[sector_col])
    pivot_df[day_col] = day_encoder.fit_transform(pivot_df[day_col])

    filtered_df = pivot_df[pivot_df[delivery_col] > min_delivery_threshold].copy()
    filtered_df["time_per_delivery"] = filtered_df[time_col] / filtered_df[delivery_col]
    Q1 = filtered_df["time_per_delivery"].quantile(0.25)
    Q3 = filtered_df["time_per_delivery"].quantile(0.75)
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    filtered_df = filtered_df[
        (filtered_df["time_per_delivery"] >= lower)
        & (filtered_df["time_per_delivery"] <= upper)
    ].drop(columns=["time_per_delivery"])

    # 2차 이상치 제거(총 시간 기준)
    Q1 = filtered_df[time_col].quantile(0.25)
    Q3 = filtered_df[time_col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    filtered_df = filtered_df[
        (filtered_df[time_col] >= lower) & (filtered_df[time_col] <= upper)
    ]

    if filtered_df.empty:
        print("이상치 제거 이후 학습 데이터가 비었습니다.")
        return None

    features = filtered_df[[sector_col, day_col, delivery_col]]
    target = filtered_df[time_col]

    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42
    )

    params = dict(
        objective="regression",
        boosting_type="gbdt",
        n_estimators=3000,
        learning_rate=0.03,
        num_leaves=63,
        min_data_in_leaf=10,  # 데이터 적으면 좀 낮춰보기
        min_gain_to_split=0.0,  # 혹시 높게 잡혀있다면 0으로
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1,
    )
    if lgbm_params:
        params.update(lgbm_params)

    model = LGBMRegressor(**params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="rmse",
        callbacks=[lgb.early_stopping(100)],
    )

    y_pred = model.predict(X_test)
    print(
        f"테스트 데이터 셋 RMSE: {mean_squared_error(y_test, y_pred) ** 0.5:.3f}, "
        f"테스트 데이터셋 R2: {r2_score(y_test, y_pred):.3f}"
    )

    return model, sector_encoder, day_encoder
