# db_handler.py
import boto3
import pandas as pd
import pymysql
import aiomysql
import os


class DBHandler:
    def __init__(self):
        # 1) 환경변수 우선 (있으면 SSM 안 탐)
        env_host = os.environ.get("DB_HOST")
        env_user = os.environ.get("DB_USER")
        env_pw = os.environ.get("DB_PASSWORD")

        if env_host and env_user and env_pw:
            self.mysql_host = env_host
            self.mysql_user = env_user
            self.mysql_password = env_pw
            self.mysql_database = os.environ.get("DB_NAME", "daas")
            self.mysql_port = int(os.environ.get("DB_PORT", "3306"))
            self.pool = None
            print("[DBHandler] using ENV for DB config")
            return

        # 2) 없으면 SSM 탐색
        ssm = boto3.client("ssm")

        # SSM 파라미터 이름 정의 (기존 그대로)
        param_names = {
            "mysql_user": "/Secure/DB_USER",
            "mysql_password": "/Secure/DB_PASSWORD",
            "mysql_host": "/Secure/DW_HOST",
            "mysql_database": "/Secure/DB_DATABASE",
        }

        self.mysql_user = self._get_ssm_parameter(ssm, param_names["mysql_user"])
        self.mysql_password = self._get_ssm_parameter(
            ssm, param_names["mysql_password"]
        )
        self.mysql_host = self._get_ssm_parameter(ssm, param_names["mysql_host"])
        self.mysql_database = self._get_ssm_parameter(
            ssm, param_names["mysql_database"]
        )

        self.mysql_port = 3306
        self.pool = None

    def _get_ssm_parameter(self, ssm, name: str) -> str:
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]

    def fetch_data(self, database: str, query: str) -> pd.DataFrame:
        """
        동기 방식 데이터 조회
        - database: "daas"
        - return: DataFrame (실패 시 빈 DF 반환)
        """

        conn = None
        try:
            conn = pymysql.connect(
                host=self.mysql_host,
                user=self.mysql_user,
                passwd=self.mysql_password,
                db=database,
                charset="utf8mb4",
                port=self.mysql_port,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5,
                read_timeout=60,
                write_timeout=60,
            )
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()

            return pd.DataFrame(results)

        except Exception as e:
            print(f"[DBHandler] Error fetching data: {e}")
            return pd.DataFrame([])

        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
