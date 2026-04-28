import pandas as pd

def predict(model, predict_df, sector_encoder, day_encoder,
            delivery_col='deliveries', sector_col='Area', day_col='day'):

    # 방어: 혹시라도 fit 안 된 encoder가 들어오면 여기서 바로 알려주기
    if not hasattr(sector_encoder, "classes_") or not hasattr(day_encoder, "classes_"):
        raise ValueError("sector_encoder/day_encoder가 fit 되지 않았습니다. train() 반환값을 그대로 넘겨주세요.")

    pred_df = (
        predict_df.groupby([sector_col, day_col])['uuid']
        .count()
        .reset_index()
        .rename(columns={'uuid': delivery_col})
    )
    print(f'pred_df {pred_df}')

    # 학습에 등장했던 카테고리만 사용 (unseen category 방지)
    pred_df = pred_df[pred_df[sector_col].isin(sector_encoder.classes_)]
    pred_df = pred_df[pred_df[day_col].isin(day_encoder.classes_)]

    if pred_df.empty:
        return pred_df.assign(
            predicted_deliveries_time=pd.Series(dtype=float),
            predicted_time_per_delivery=pd.Series(dtype=float),
        )

    # 인코딩
    pred_df[sector_col] = sector_encoder.transform(pred_df[sector_col])
    pred_df[day_col]    = day_encoder.transform(pred_df[day_col])

    pred_features = pred_df[[sector_col, day_col, delivery_col]]
    print(f'pred_features: {pred_features}')

    # 예측
    pred_df['predicted_deliveries_time'] = model.predict(pred_features)

    # (중요) 사람이 읽는 값으로 복원해서 반환
    pred_df[sector_col] = sector_encoder.inverse_transform(pred_df[sector_col])
    pred_df[day_col]    = day_encoder.inverse_transform(pred_df[day_col])

    pred_df['predicted_time_per_delivery'] = (
        pred_df['predicted_deliveries_time'] / pred_df[delivery_col]
    )

    return pred_df