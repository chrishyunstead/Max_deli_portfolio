import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


def push_to_spreadsheet(merged_df: pd.DataFrame):
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sa_path = os.path.join(base_dir, "sa.json")
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    gc = gspread.authorize(creds)

    sheet_id = os.environ["SHEET_ID"]
    target_tab = os.environ.get("WORKSHEET") or "max"  # ✅ 빈 문자열도 기본값 처리

    # 탭이 없으면 자동 생성(처음 배포 시 편함)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(target_tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=target_tab, rows="100", cols="26")

    ws.clear()
    ws.format("C:C", {"numberFormat": {"type": "NUMBER", "pattern": "0"}})
    ws.format("D:D", {"numberFormat": {"type": "NUMBER", "pattern": "0.########"}})
    ws.format("E:E", {"numberFormat": {"type": "NUMBER", "pattern": "0"}})
    ws.format("F:F", {"numberFormat": {"type": "NUMBER", "pattern": "0"}})

    if merged_df.empty:
        print(f"[{target_tab}] 결과가 비어 있어 시트만 초기화했습니다.")
        return

    print(f"merged_df.columns: {merged_df.columns}")

    values = [merged_df.columns.tolist()] + merged_df.values.tolist()

    print(f"[{target_tab}] upload rows={len(merged_df)} cols={len(merged_df.columns)}")
    ws.update("A1", values, value_input_option="RAW")
    print(f"✅ 구글 시트 업로드 완료! {len(merged_df)} rows → {target_tab}")
