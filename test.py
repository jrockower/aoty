import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from df2gspread import df2gspread as d2g

d = {'col1': [1, 2], 'col2': [3, 4]}
df = pd.DataFrame(data=d)

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    'service_account.json', scope)

gc = gspread.authorize(credentials)

df = pd.read_csv('output.csv', index_col=False)

spreadsheet_key = '1vpxZunN4M8gvnsireG4TEPSlA-pxo8Ta9Y6Kj8zgWwg'
wks_name = 'Sheet1'
d2g.upload(df, spreadsheet_key, wks_name,
           credentials=credentials, row_names=True)
