import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from df2gspread import df2gspread as d2g

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    'service_account.json', scope)

gc = gspread.authorize(credentials)

df = pd.read_csv('output.csv')

spreadsheet_key = '1vpxZunN4M8gvnsireG4TEPSlA-pxo8Ta9Y6Kj8zgWwg'
wks_name = 'raw'
d2g.upload(df, spreadsheet_key, wks_name,
           credentials=credentials, row_names=True)
