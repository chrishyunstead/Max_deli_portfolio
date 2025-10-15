import pandas as pd

def process_available_delivery_time(df_time):

    duplicated_pairs_available_delivery_time = (
    df_time.groupby(['date', 'user_id'])
    .filter(lambda x: len(x) > 1)
    .index
    )

    available_delivery_time_cleaned = df_time.drop(index=duplicated_pairs_available_delivery_time).reset_index(drop=True)

    # 섹터 끼리의 이상치 제거
    available_delivery_time_cleaned_sector = available_delivery_time_cleaned['area'].unique()

    filtered_available_dfs = []

    for s in available_delivery_time_cleaned_sector:
        filtered_available_df = available_delivery_time_cleaned[available_delivery_time_cleaned['area']==s]
        Q1 = filtered_available_df['available_delivery_time'].quantile(0.25)
        Q3 = filtered_available_df['available_delivery_time'].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        filtered_available_df = filtered_available_df[(filtered_available_df['available_delivery_time'] >= lower) & 
                                (filtered_available_df['available_delivery_time'] <= upper)].drop(columns = ['user_id'])

        filtered_available_dfs.append(filtered_available_df)

    available_delivery_time_no_outlier = pd.concat(filtered_available_dfs, ignore_index=True)
    
    available_delivery_time_no_outlier_sector=available_delivery_time_no_outlier.groupby('area')['available_delivery_time'].mean().reset_index()

    return available_delivery_time_no_outlier_sector