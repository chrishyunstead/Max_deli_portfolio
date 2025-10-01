# data_import_sheets.py
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _gc():
    creds = Credentials.from_service_account_file("sa.json", scopes=SCOPES)
    return gspread.authorize(creds)

def _read_tab(sheet_id: str, tab: str, header_row: int = 1) -> pd.DataFrame:
    gc = _gc()
    ws = gc.open_by_key(sheet_id).worksheet(tab)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    header = values[header_row-1]
    rows = values[header_row:]
    df = pd.DataFrame(rows, columns=header)
    # 숫자 컬럼 자동 변환 시도(실패해도 무시)
    for c in df.columns:
        try: df[c] = pd.to_numeric(df[c])
        except: pass
    return df

class SheetDataLoader:
    def __init__(self):
        self.sheet_id = os.environ["SHEET_ID"]
        self.tab_model    = os.environ.get("TAB_MODEL", "rf")
        self.tab_time     = os.environ.get("TAB_TIME", "available_time")
        self.tab_predict  = os.environ.get("TAB_PREDICT", "shipping")
        self.tab_schedule = os.environ.get("TAB_SCHEDULE", "schedule")

    def fetch_all_data(self):
        df_model    = _read_tab(self.sheet_id, self.tab_model)
        df_time     = _read_tab(self.sheet_id, self.tab_time)
        predict_df  = _read_tab(self.sheet_id, self.tab_predict)
        df_schedule = _read_tab(self.sheet_id, self.tab_schedule)
        return df_model, df_time, predict_df, df_schedule
