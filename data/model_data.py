# import awswrangler as wr

# def model_data(workflow_date: str):
#     # Athena → pandas (회귀 모델 피처 쿼리)
#     df_model = wr.athena.read_sql_query(
#         sql=f"""
#             SELECT * 
#             FROM "postalcode_clustering"."regression_features"
#             WHERE dt = '{workflow_date}' 
#             """,
#         database="postalcode_clustering",
#         ctas_approach=False
#     )

#     # Athena → pandas (잔여시간 쿼리)
#     df_time = wr.athena.read_sql_query(
#         sql=f"""
#             SELECT * 
#             FROM "postalcode_clustering"."delivery_time" 
#             WHERE dt = '{workflow_date}' 
#             """,
#         database="postalcode_clustering",
#         ctas_approach=False
#     )

#     return df_model, df_time

class ModelProcessor:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def fetch_model(self, workflow_date):
        query = f"""
            WITH base AS (
                SELECT
                    ss.tracking_number,
                    DATE_FORMAT(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR), '%Y-%m-%d') AS Date,
                    REGEXP_REPLACE(ls.code, '[0-9]', '') AS Area,
                    sc.container_class AS color,
                    DATE_ADD(ss.timestamp_delivery_complete, INTERVAL 9 HOUR) AS timestamp_delivery_complete,
                    LOWER(DAYNAME(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR))) AS day,
                    sc.user_id AS user_id
                FROM shipping_shippingitem ss
                JOIN location_sector ls ON ss.designated_sector_id = ls.id
                JOIN shipping_container sc ON ss.shipping_container_id = sc.id
                WHERE ss.timestamp_delivery_complete IS NOT NULL
                AND ss.timestamp_outfordelivery IS NOT NULL
                AND ss.timestamp_delivery_incomplete IS NULL
                AND ls.allowed = 1
                AND ls.code NOT IN ('취소')
                AND TIME(DATE_ADD(ss.timestamp_delivery_complete, INTERVAL 9 HOUR)) BETWEEN '17:00:00' AND '23:59:59'
                AND TIME(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN '17:00:00' AND '20:00:00'
                AND DATE(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN DATE_SUB('{workflow_date}', INTERVAL 30 DAY) AND '{workflow_date}'
            ),
            agg AS (
                SELECT
                    Date,
                    Area,
                    user_id,
                    color,
                    day,
                    COUNT(tracking_number) AS deliveries,
                    SEC_TO_TIME(TIMESTAMPDIFF(SECOND, MIN(timestamp_delivery_complete), MAX(timestamp_delivery_complete))) AS deliveries_time,
                    SEC_TO_TIME(
                        CASE
                            WHEN COUNT(tracking_number) > 1 THEN
                                TIMESTAMPDIFF(SECOND, MIN(timestamp_delivery_complete), MAX(timestamp_delivery_complete)) / (COUNT(tracking_number) - 1)
                            ELSE 0
                        END
                    ) AS time_per_delivery
                FROM base
                GROUP BY Date, color, user_id, Area, day
            ),
            area_guard AS (
                SELECT
                    Date,
                    user_id,
                    COUNT(DISTINCT Area) AS area_cnt
                FROM agg
                GROUP BY Date, user_id
            )
            SELECT
                a.Date,
                a.Area,
                a.user_id,
                a.color,
                a.day,
                a.deliveries,
                a.deliveries_time,
                a.time_per_delivery
            FROM agg a
            JOIN area_guard g
            ON a.Date = g.Date AND a.user_id = g.user_id
            WHERE
                g.area_cnt = 1                       
                AND a.deliveries >= 15
                AND a.deliveries < 70
                AND a.time_per_delivery <= '00:20:00'
                AND a.user_id <> 464
            ORDER BY
                a.Area, a.Date;
        """
        return self.db_handler.fetch_data("daas", query)