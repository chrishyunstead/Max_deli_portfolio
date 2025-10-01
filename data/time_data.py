class TimeProcessor:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def fetch_time(self, workflow_date):
        query = f"""
            WITH base AS (
                SELECT
                    DATE(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR)) AS date,
                    REGEXP_REPLACE(ls.code, '[0-9]', '') AS area,
                    LOWER(DAYNAME(DATE_ADD(ss.timestamp_boxassigned, INTERVAL 9 HOUR))) AS day,
                    sc.user_id AS user_id,
                    DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR) AS out_kst,
                    DATE_ADD(ss.timestamp_delivery_complete, INTERVAL 9 HOUR) AS comp_kst,
                    ss.uuid
                FROM shipping_shippingitem ss
                JOIN location_sector ls
                    ON ss.designated_sector_id = ls.id
                JOIN shipping_container sc
                    ON ss.shipping_container_id = sc.id
                WHERE ss.timestamp_delivery_complete IS NOT NULL
                AND ss.timestamp_delivery_incomplete IS NULL
                AND ls.allowed = 1
                AND ls.code NOT IN ('취소')
                -- 완주 시각(로컬) 17:00~23:59
                AND TIME(DATE_ADD(ss.timestamp_delivery_complete, INTERVAL 9 HOUR))
                        BETWEEN '17:00:00' AND '23:59:59'
                -- 출차 시각(로컬) 17:00~20:00
                AND TIME(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR))
                        BETWEEN '17:00:00' AND '20:00:00'
                -- 최근 30일
                AND DATE(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR))
                        BETWEEN DATE_SUB('{workflow_date}', INTERVAL 30 DAY) AND '{workflow_date}'
            ),
            agg AS (
                SELECT
                    date,
                    area,
                    day,
                    user_id,
                    MIN(out_kst)  AS first_out_kst,
                    MIN(comp_kst) AS first_comp_kst,
                    COUNT(uuid)   AS deliveries   -- 배정 물량
                FROM base
                GROUP BY date, area, day, user_id
            ),
            area_guard AS (
                -- 같은 날 같은 user가 여러 area에 걸치면 제외하기 위한 가드
                SELECT
                    date,
                    user_id,
                    COUNT(DISTINCT area) AS area_cnt
                FROM agg
                GROUP BY date, user_id
            )
            SELECT
                a.date,
                GREATEST(
                    (86400 - TIME_TO_SEC(TIME(a.first_out_kst)))
                    - TIMESTAMPDIFF(SECOND, a.first_out_kst, a.first_comp_kst),
                    0
                ) AS available_delivery_time,
                a.area,
                a.day,
                a.user_id,
                a.deliveries
            FROM agg a
            JOIN area_guard g
            ON a.date = g.date AND a.user_id = g.user_id
            WHERE
                g.area_cnt = 1                           
                AND a.area IS NOT NULL
                AND a.day IS NOT NULL
                AND a.day = LOWER(DAYNAME('{workflow_date}')
                AND a.deliveries >= 15
                AND a.deliveries < 70
            ORDER BY
                a.date, available_delivery_time, a.area;
        """
        return self.db_handler.fetch_data("daas", query)