# model_processor.py
class ModelDatasetQuery:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def fetch_dataset_df(self):
        query = r"""
            WITH base AS (
            SELECT
                ss.tracking_number,
                DATE_FORMAT(DATE_ADD(st.timestamp_outfordelivery, INTERVAL 9 HOUR), '%Y-%m-%d') AS Date,
                REGEXP_REPLACE(ls.code, '[0-9]', '') AS Area,
                sc.container_class AS color,
                DATE_ADD(st.timestamp_delivery_complete, INTERVAL 9 HOUR) AS ts_complete,
                DATE_ADD(st.timestamp_outfordelivery, INTERVAL 9 HOUR) AS ts_out,
                LOWER(DAYNAME(DATE_ADD(st.timestamp_outfordelivery, INTERVAL 9 HOUR))) AS day,
                sc.user_id AS user_id
            FROM shipping_shippingitem ss
            JOIN location_sector ls ON ss.designated_sector_id = ls.id
            JOIN shipping_container sc ON ss.shipping_container_id = sc.id
            JOIN shipping_shippingitemtimetable st ON ss.id = st.shipping_item_id
            WHERE st.timestamp_delivery_complete IS NOT NULL
                AND st.timestamp_outfordelivery IS NOT NULL
                AND st.timestamp_delivery_incomplete IS NULL
                AND ls.allowed = 1
                AND ls.code NOT IN ('취소')
                AND (TIME(DATE_ADD(st.timestamp_delivery_complete, INTERVAL 9 HOUR)) BETWEEN '17:00:00' AND '23:59:59'
                OR TIME(DATE_ADD(st.timestamp_delivery_complete, INTERVAL 9 HOUR)) < '03:00:00')
                AND TIME(DATE_ADD(st.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN '17:00:00' AND '20:00:00'
                AND DATE(DATE_ADD(st.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN DATE_SUB(CURDATE(), INTERVAL 90 DAY) AND CURDATE()
            ),
            agg AS (
            SELECT
                Date,
                Area,
                user_id,
                color,
                day,
                COUNT(tracking_number) AS deliveries,
                TIMESTAMPDIFF(SECOND, MIN(ts_out), MAX(ts_complete)) AS deliveries_seconds,
                CASE WHEN COUNT(*) > 0 THEN
                    TIMESTAMPDIFF(SECOND, MIN(ts_out), MAX(ts_complete)) / COUNT(*)
                ELSE 0 END AS per_drop_seconds
            FROM base
            GROUP BY Date, Area, user_id, color, day
            ),
            area_guard AS (
            SELECT Date, user_id, COUNT(DISTINCT Area) AS area_cnt
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
            SEC_TO_TIME(a.deliveries_seconds) AS deliveries_time,
            SEC_TO_TIME(a.per_drop_seconds)    AS time_per_delivery
            FROM agg a
            JOIN area_guard g
            ON a.Date = g.Date AND a.user_id = g.user_id
            WHERE
            g.area_cnt = 1
            AND a.deliveries >= 15
            AND a.deliveries < 70
            AND SEC_TO_TIME(a.per_drop_seconds) <= '00:20:00'
            AND a.user_id <> 464
            ORDER BY
            a.Area, a.Date
        """
        return self.db_handler.fetch_data("daas", query)
