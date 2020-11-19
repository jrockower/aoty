import requests
import re
import csv
import argparse
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
        id_split = re.split(r'\s-\s', album_info)
        self.artist, self.title = id_split
        self.position = position
        self.date = tag.find_next('div', {'class': 'albumListDate'}).text
        self.genre = tag.find_next('div', {'class': 'albumListGenre'}).text
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
    tag = soup.find('div', {'class': 'albumListCover mustHear'})

    for i in range(1, 51):
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


def write_to_csv(table_data, filename):
    '''
    Write scraped data to a csv file
    Inputs: table_data (list of lists)
            filename (str)
    '''

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(table_data)


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

    for line in open('args.txt', 'r'):
        link, pub = line.split()
        data = get_list(link, pub)
        df = df.append(pd.DataFrame(data, columns=df.columns))

    df.to_csv(args.out, index=False)

    if args.g:
        push_to_gsheets(args.out, args.cred)
    else:
        print('''\nSkipping Google Sheets Upload.\nIf you would like to upload to Google Sheets, please rerun using python3 scraper.py --g''')
