import requests
import re
import pandas as pd
import numpy as np
import csv
import argparse
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AOTY Entry')
    parser.add_argument('--out', metavar='Export File Path', type=str,
                        default='output.csv')
    args = parser.parse_args()

    df = pd.DataFrame(columns=['Position', 'Publication',
                               'Artist', 'Title', 'Genre', 'Release Date',
                               'Spotify Link'])

    for line in open('args.txt', 'r'):
        link, pub = line.split()
        data = get_list(link, pub)
        df = df.append(pd.DataFrame(data, columns=df.columns))

    df.to_csv(args.out, index=False)

