import pandas as pd
import pymysql
from sshtunnel import SSHTunnelForwarder
import os
from dotenv import load_dotenv

class AutoContainerGeneration:
    def __init__(self, version=2, debug=False):
        self.version = version
        self.debug = debug
        print(f"AutoContainerGeneration version: {version}")

        # 로컬 테스트일 때만 .env 읽기
        if os.path.exists(".env"):
            load_dotenv()

    # 공통 MySQL 데이터 추출 메서드
    def fetch_data(self, query, ssh_host, ssh_user, ssh_private_key, mysql_host, mysql_port, mysql_user, mysql_password, mysql_database):
        """
        MySQL 데이터를 추출하여 DF로 변환
        """
        try:
            with SSHTunnelForwarder(
                (ssh_host, 22),
                ssh_username=ssh_user,
                ssh_private_key=ssh_private_key,
                remote_bind_address=(mysql_host, mysql_port)
            ) as tunnel:
                print("SSH 터널 연결 성공")

                with pymysql.connect(
                    host='127.0.0.1', 
                    user=mysql_user,
                    passwd=mysql_password,
                    db=mysql_database,
                    charset='utf8',
                    port=tunnel.local_bind_port,
                    cursorclass=pymysql.cursors.DictCursor) as conn:
                    with conn.cursor() as cur:
                        cur.execute(query)
                        results = cur.fetchall()
                        print("쿼리 실행 완료")

                        # 결과를 DF로 변환

                        df = pd.DataFrame(results)
                        return df

        except Exception as e:
            print(f"Error fetching data for: {e}")
            return None

    # 전체 데이터 추출
    def fetch_all_data(self):
        """
        MySQL 쿼리를 실행하여 Shipping Items와 Bunny Schedule 데이터를 DF로 변환
        """
        # SSH 및 MySQL 설정
        ssh_host = os.getenv("SSH_HOST_VER_1")
        ssh_user = os.getenv("SSH_USER")
        ssh_private_key = os.getenv("SSH_PRIVATE_KEY_PATH", "/tmp/ssh_key.pem")  # 경로 사용
        

        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = 3306
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")
        mysql_database = os.getenv("MYSQL_DATABASE")


        random_forest_query = """
        WITH base AS (
            SELECT
                ss.tracking_number,
                DATE_FORMAT(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR), '%Y-%m-%d') AS Date,
                REGEXP_REPLACE(ls.code, '[0-9]', '') AS Area,
                sc.container_class AS color,
                DATE_ADD(ss.timestamp_delivery_complete, INTERVAL 9 HOUR) AS timestamp_delivery_complete,
                DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR) AS timestamp_outfordelivery,
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
            AND TIME(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN '17:00:00' AND '21:00:00'
            AND DATE(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR)) BETWEEN DATE_SUB(CURDATE(), INTERVAL 90 DAY) AND CURDATE()
        ),
        agg AS (
            SELECT
                Date,
                Area,
                user_id,
                color,
                day,
                COUNT(tracking_number) AS deliveries,
                SEC_TO_TIME(TIMESTAMPDIFF(SECOND, MAX(timestamp_outfordelivery), MAX(timestamp_delivery_complete))) AS deliveries_time,
                SEC_TO_TIME(
                    CASE
                        WHEN COUNT(tracking_number) > 1 THEN
                            TIMESTAMPDIFF(SECOND, MAX(timestamp_outfordelivery), MAX(timestamp_delivery_complete)) / (COUNT(tracking_number) - 1)
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

        time_query = """
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
                -- 출차 시각(로컬) 17:00~21:00
                AND TIME(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR))
                        BETWEEN '17:00:00' AND '21:00:00'
                -- 최근 30일
                AND DATE(DATE_ADD(ss.timestamp_outfordelivery, INTERVAL 9 HOUR))
                        BETWEEN DATE_SUB(CURDATE(), INTERVAL 90 DAY) AND CURDATE()
            ),
            agg AS (
                SELECT
                    date,
                    area,
                    day,
                    user_id,
                    MAX(out_kst)  AS first_out_kst,
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
                AND a.day = LOWER(DAYNAME(CURDATE()))
                AND a.deliveries >= 15
                AND a.deliveries < 70
            ORDER BY
                a.date, available_delivery_time, a.area;
            """

        shipping_query = """
        SELECT
            shipping_shippingitem.uuid,
            REGEXP_REPLACE(location_sector.code, '[0-9]', '') as Area
        FROM shipping_shippingitem 
        LEFT JOIN order_order
        ON shipping_shippingitem.order_id = order_order.id
        LEFT JOIN shop_shop 
        ON order_order.shop_id = shop_shop.id
        LEFT JOIN location_sector
        ON shipping_shippingitem.designated_sector_id = location_sector.id
        left JOIN location_address
        on shipping_shippingitem.address_id = location_address.id
        left join route_pickupbatch
        on shipping_shippingitem.pickup_batch_id = route_pickupbatch.id
        WHERE shop_shop.id not iN (1,3)
        AND DATE_ADD(shipping_shippingitem.timestamp_created, INTERVAL 9 HOUR) >= DATE_ADD(DATE_ADD(NOW(), INTERVAL 9 HOUR), INTERVAL -3 day)
        AND (
            JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) IS NULL
            OR JSON_UNQUOTE(JSON_EXTRACT(order_order.metadata, '$.delivery_date')) NOT IN (
                DATE_FORMAT(
                    DATE_ADD(CONVERT_TZ(NOW(), '+00:00', '+09:00'), INTERVAL 1 DAY),
                    '%Y%m%d'
                )
                )
        )
        AND shipping_shippingitem.timestamp_delivery_complete IS NULL;
        """

        schedule_query = """
        SELECT
            dispatch_dataset.uuid as 'uuid',
            dispatch_dataset.requested_date as 'Date',
            dispatch_dataset.bunny_color as 'Type',
            location_sector.code as 'code',
            dispatch_dataset.dispatch_status,
            dispatch_dataset.fullname,
            REPLACE(REGEXP_REPLACE(location_sector.code, '[0-9]', ''), '_', '') as 'Area'
        FROM location_sector
        JOIN (
            SELECT
                dispatch_dispatch.requested_date as 'requested_date',
                dispatch_schedule.bunny_color as 'bunny_color',
                dispatch_dispatch.dispatch_status,
                user_profile_rider.fullname,
                auth_user.uuid as 'uuid',
                CAST(JSON_EXTRACT(dispatch_dispatch.sector_list, '$[0]') AS UNSIGNED) AS 'sector_id'
            FROM dispatch_dispatch
            JOIN dispatch_schedule
            ON dispatch_dispatch.schedule_id = dispatch_schedule.id
            JOIN auth_user
            ON dispatch_schedule.rider_id = auth_user.id
            JOIN user_profile_rider
            ON user_profile_rider.user_id = auth_user.id
            WHERE dispatch_dispatch.schedule_id IS NOT NULL
            AND dispatch_dispatch.dispatch_status IN ('SUBMITTED', 'CONFIRMED', 'UNDISPATCHED', 'REFUSED', 'PENDING')
            AND dispatch_dispatch.requested_date = CURDATE()
            AND dispatch_schedule.bunny_color NOT IN ('OFFROAD')
        ) dispatch_dataset
        ON location_sector.id = dispatch_dataset.sector_id
        order by 4;
        """

        # 각 쿼리 결과를 DataFrame으로 가져오기
        
        random_forest = self.fetch_data(random_forest_query, ssh_host, ssh_user, ssh_private_key,
                                                  mysql_host, mysql_port, mysql_user, mysql_password, mysql_database)
        
        time = self.fetch_data(time_query, ssh_host, ssh_user, ssh_private_key,
                                                  mysql_host, mysql_port, mysql_user, mysql_password, mysql_database)
        
        shipping = self.fetch_data(shipping_query, ssh_host, ssh_user, ssh_private_key,
                                                  mysql_host, mysql_port, mysql_user, mysql_password, mysql_database)
        
        schedule = self.fetch_data(schedule_query, ssh_host, ssh_user, ssh_private_key,
                                                  mysql_host, mysql_port, mysql_user, mysql_password, mysql_database)

        return random_forest, time, shipping, schedule