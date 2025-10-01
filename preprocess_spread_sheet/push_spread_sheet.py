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


import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def push_to_spreadsheet(merged_df):
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # ✅ GitHub Actions에서 Secrets: JSON_KEY_PATH 로 저장했으므로 아래처럼 변경
    with open("sa.json", "w") as f:
        f.write(os.environ["JSON_KEY_PATH"])

    creds = Credentials.from_service_account_file("sa.json", scopes=scopes)
    gc = gspread.authorize(creds)

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1ciVZdzU6GnlV8YZuo0frIOmsoaAdGngNLBgE4cDBjek/edit#gid=0"
    doc = gc.open_by_url(spreadsheet_url)
    sheet = doc.worksheet("max")

    sheet.clear()
    values = [merged_df.columns.tolist()] + merged_df.values.tolist()
    sheet.update('A1', values)

    return print("✅ 구글 시트 업로드 완료!")

