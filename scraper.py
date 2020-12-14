import requests
import re
import csv
import argparse
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from df2gspread import df2gspread as d2g
from bs4 import BeautifulSoup

class Album:

    def __init__(self, album_info, tag, position, pub):
        '''
        Creates an Album object
        Inputs: album_info (str): concatenated artist and album title
                tag: a BeautifulSoup tag object
                position (str): the position on a list
                pub (str): the publication title
        '''
        id_split = re.split(r'\s-\s', album_info, maxsplit=1)
        self.artist, self.title = id_split
        self.position = position
        self.date = tag.find_next('div', {'class': 'albumListDate'}).text
        try:
            self.genre = tag.find_next('div', {'class': 'albumListGenre'}).text
        except Exception:
            self.genre = ""
        try:
            self.spotify = tag.find_next('div', {'class': 'albumListLinks'}). \
                           find('a', {'data-track-action': 'Spotify'})['href']
        except Exception:
            self.spotify = 'No Spotify Link Found'

        self.publication = pub

    def get_album(self):
        '''
        Method to get a list of the relevant fields for an Album object
        '''
        print('Getting', str(self), '\n-----------')
        return [self.position, self.publication, self.artist, self.title,
                self.genre, self.date, self.spotify]

    def __repr__(self):
        return self.artist + ' - ' + self.title + '\nPosition #' + \
               self.position + ' in ' + self.publication


def get_list(url, pub):
    '''
    Get Top 50 list from an albumoftheyear.org URL
    Inputs: url (str) - a string containing the URL of an AOTY list, sorted
                        in ascending order (top album first)
            pub (str) - the publication name
    Returns: a Pandas dataframe
    '''

    print('Processing:', url)

    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html5lib')

    table_data = []
    centercontent = soup.find('div', {'id': 'centerContent'})
    position = centercontent.find('span', {'itemprop': 'position'}).text
    album_info = centercontent.find_next('meta')['content']
    tag = soup.find(
        'div', {'class': ['albumListCover mustHear', 'albumListCover']})

    while True and position != '51':
        album = Album(album_info, tag, position, pub)
        table_data.append(album.get_album())
        try:
            position = tag.find_next('span', {'itemprop': 'position'}).text
        except AttributeError:
            print('Finished Processing: Breaking out of Loop')
            break
        album_info = tag.find_next('meta')['content']
        tag = tag.find_next('div', {'class': ['albumListCover mustHear', 'albumListCover']})

    return table_data


def reshape_data(df):
    '''
    Reshape wide to long depending on how we would like to display the data.
    Inputs: df - a Pandas dataframe
    Returns: a tuple containing the reshaped data and the unique number of
             publications
    '''

    data = df.pivot_table(index=["Artist", "Title"],
                          values="Position",
                          columns=["Publication"],
                          aggfunc='first').reset_index()

    # Drop duplicates and retain main fields
    deduped = df.drop_duplicates(subset=['Artist', 'Title']).iloc[:, 2:]

    joined = data.merge(deduped, how='inner', on=['Artist', 'Title'])

    joined.index.name = 'Index'

    return joined


def calc_stats(df, pub_list):
    '''
    Calculate main metrics used for final workbook.
    Input: df - a Pandas dataframe
           pub_list (list) - list of publications
    Returns: a Pandas dataframe with additional columns for stats
    '''

    df[pub_list] = df[pub_list].apply(pd.to_numeric)
    df['avg'] = df[pub_list].mean(axis=1)
    df['cons_score'] = (df[pub_list].sum(axis=1) + 75 *
                        (len(pub_list) - df[pub_list].count(axis=1))) / len(pub_list)
    df['num_lists'] = df[pub_list].count(axis=1)
    df['count_1'] = (df[pub_list] == 1).sum(1)
    df['count_top10'] = (df[pub_list] <= 10).sum(1)

    df.sort_values(by='cons_score', inplace=True)

    return df


def push_to_gsheets(path, cred):
    '''
    Push a Pandas dataframe to Google Sheets
    Input: path (str) - path to csv
           cred (str) - credentials file name
    '''

    print('\nUploading to Google Sheets...\n')
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        cred, scope)

    gc = gspread.authorize(credentials)

    df = pd.read_csv(path)
    df = df.astype(str)
    df = df.replace('nan', '', regex=True)

    spreadsheet_key = '1vpxZunN4M8gvnsireG4TEPSlA-pxo8Ta9Y6Kj8zgWwg'
    wks_name = 'raw'

    d2g.upload(df, spreadsheet_key, wks_name,
            credentials=credentials, row_names=True)

    print('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AOTY Entry')
    parser.add_argument('--out', metavar='Export File Path', type=str,
                        default='output.csv')
    parser.add_argument('--g', action='store_true',
                        default=False)
    parser.add_argument('--cred', metavar='Credentials Name', type=str,
                        default='service_account.json')

    args = parser.parse_args()

    df = pd.DataFrame(columns=['Position', 'Publication',
                               'Artist', 'Title', 'Genre', 'Release Date',
                               'Spotify Link'])

    pub_list = []
    for line in open('args.txt', 'r'):
        link, pub = line.split()
        pub_list.append(pub)
        data = get_list(link, pub)
        df = df.append(pd.DataFrame(data, columns=df.columns))

    df = reshape_data(df)
    df = calc_stats(df, pub_list)
    # Reorder the columns
    cols = df.columns.tolist()
    cols = cols[:2] + cols[-8:] + cols[2:-8]
    df = df[cols]

    df.to_csv(args.out, index=False)

    if args.g:
        push_to_gsheets(args.out, args.cred)
    else:
        print('''\nSkipping Google Sheets Upload.\nIf you would like to upload to Google Sheets, please rerun using python3 scraper.py --g''')
