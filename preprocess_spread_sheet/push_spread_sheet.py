# import pandas as pd
# from oauth2client.service_account import ServiceAccountCredentials
# import gspread
# from pathlib import Path

# def push_to_spreadsheet(merged_df):
#     scope = [
#         'https://spreadsheets.google.com/feeds',
#         'https://www.googleapis.com/auth/drive'
#     ]

#     # 서비스 계정 키(JSON)

#     base_dir = Path(__file__).resolve().parent    # 현재 py 파일이 있는 폴더
#     json_key_path = (base_dir / "../max-delivery-key.json").resolve()
    
#     credential = ServiceAccountCredentials.from_json_keyfile_name(json_key_path, scope)
#     gc = gspread.authorize(credential)

#     # 구글 스프레드시트 열기
#     spreadsheet_url = "https://docs.google.com/spreadsheets/d/1ciVZdzU6GnlV8YZuo0frIOmsoaAdGngNLBgE4cDBjek/edit#gid=0"
#     doc = gc.open_by_url(spreadsheet_url)

#     # 시트 선택
#     sheet = doc.worksheet("max")

#     # ======================================
#     # 1) 데이터 읽어오기 (예시)
#     df = pd.DataFrame(sheet.get_all_values())
#     df.rename(columns=df.iloc[0], inplace=True)
#     df = df.drop(df.index[0])
#     print("원본 데이터:\n", df.head())


#     print("업데이트할 데이터:\n", merged_df)

#     # ======================================
#     # 3) DataFrame → 구글시트 쓰기
#     # 기존 시트 내용 삭제 후 DataFrame 업로드
#     sheet.clear()

#     # 헤더 + 데이터 합치기
#     values = [merged_df.columns.tolist()] + merged_df.values.tolist()
#     sheet.update('A1', values)

#     return print("✅ 구글 시트 업로드 완료!")


# preprocess_spread_sheet/push_spread_sheet.py
# preprocess_spread_sheet/push_spread_sheet.py
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import gspread

def push_to_spreadsheet(merged_df: pd.DataFrame):
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file("sa.json", scopes=scopes)
    gc = gspread.authorize(creds)

    sheet_id = os.environ["SHEET_ID"]
    target_tab = os.environ.get("WORKSHEET") or "max"   # ✅ 빈 문자열도 기본값 처리

    # 탭이 없으면 자동 생성(처음 배포 시 편함)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(target_tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=target_tab, rows="100", cols="26")

    ws.clear()
    if merged_df.empty:
        print(f"[{target_tab}] 결과가 비어 있어 시트만 초기화했습니다.")
        return

    values = [merged_df.columns.tolist()] + merged_df.values.tolist()
    ws.update("A1", values, value_input_option="RAW")
    print(f"✅ 구글 시트 업로드 완료! {len(merged_df)} rows → {target_tab}")

