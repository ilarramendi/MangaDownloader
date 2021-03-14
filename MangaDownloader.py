import requests
from time import sleep
from PIL import Image, ImageFile
from subprocess import call
from glob import glob
from os import path
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import sys
import time
from datetime import timedelta
from zipfile import ZipFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
delay = 1
providersFile = './mangas.json'
filePath = "/media/e/manga/$PNAME/$PNAME - $CP [$PROV][$LANG].$EXT"
rootpt = '/media/e/manga/'
Mangas = []
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
providers = [
        {'id': 'submanga',
        "imageUrl": "https://submanga.io/uploads/manga/$ID/chapters/$CHAPTER/$IMG.jpg",
        "chaptersUrl": "https://submanga.io/manga/$ID",
        "pagesUrl": "https://submanga.io/manga/$ID/$CHAPTER",
        "defaultLang": 'es'},
        {'id': 'kissmanga',
        "imageUrl": "https://kissmanga.org/chapter/$ID/chapter_$CHAPTER",
        "chaptersUrl": "https://kissmanga.org/manga/$ID",
        "defaultLang": 'en'}
    ]

if path.exists(providersFile):
    with open(providersFile, 'r') as json_file:
        Mangas = json.load(json_file)

def parseChapter(cp):
    info = cp.partition('.')
    return "{:<7}".format(info[0].zfill(4) + ('_' + info[2] if info[2] != '' else ''))

def downloadImage(url, path, retry, delay):
    response = requests.get(url)
    i = 0
    sleep(delay)
    while response.status_code != 200 and i < retry:
        response = requests.get(url)
        sleep(delay)
        i += 1

    if response.status_code == 200:
        file = open(path, 'wb')
        file.write(response.content)
        file.close()
        return True
    else: 
        print('Failed to download: ' + url)
        return False

def downloadChapterSubmanga(manga, chapter, ext):
    start = time.time()
    Manga = providers['submanga']['mangas'][manga]
    imgUrl = providers['submanga']['imageUrl'].replace('$ID', manga).replace('$CHAPTER', chapter)
    call(['rm', './images', '-r'])
    call(['mkdir', './images'])


    #Get # of pages
    pages = int(BeautifulSoup(requests.get(providers['submanga']['pagesUrl'].replace('$ID', manga).replace('$CHAPTER', chapter)).text, "html.parser").select("select.selectpicker option")[-1].text)

    useZero = requests.get(imgUrl.replace('$IMG', '01')).status_code == 200
    i = 1
    start2 = time.time()
    while i < pages and downloadImage(imgUrl.replace('$IMG', '0' + str(i) if useZero and i<=9 else str(i)), "./images/" + str(i).zfill(4) + '.jpg', 3, delay):
        print('\rSuccesfully downloaded ' + Manga['name'] + ' ' + chapter + ' page [' + str(i) + '/' + str(pages) + ']', end='')
        start2 = time.time()
        i += 1

    if i == pages:
        pt = filePath.replace('$PNAME', Manga['name']).replace('$CP', parseChapter(chapter)).replace('$PROV', 'submanga').replace('$LANG', Manga['language'])
        if ext == 'PDF': saveAsPDF(pt.replace('$EXT', 'pdf'))
        elif ext == 'CBZ': saveAsCBZ(pt.replace('$EXT', 'cbz'))

        print('\rSuccesfully Downloaded ' + Manga['name'] + ' ' + chapter + ' with ' + str(i) + ' pages and saved as ' + ext + ' in ' + str(timedelta(seconds=round(time.time() - start))))
        providers['submanga']['mangas'][manga]['chapters'][chapter] = True
        with open(providersFile, 'w') as outfile: json.dump(providers, outfile, indent=4)
    else: print('\rError Downloading, missing pages.')

def downloadChapterKissmanga(manga, chapter, ext):
    start = time.time()
    Manga = providers['kissmanga']['mangas'][manga]
    call(['rm', './images', '-r'])
    call(['mkdir', './images'])
    images = BeautifulSoup(requests.get(providers['kissmanga']['imageUrl'].replace('$ID', manga).replace('$CHAPTER', chapter)).text, "html.parser").select("div#centerDivVideo img")
    i = 0
    while i < len(images) and downloadImage(images[i]['src'], './images/' + str(i).zfill(4) + '.jpg', 3, delay):
        print('\rSuccesfully downloaded ' + Manga['name'] + ' ' + chapter + ' page [' + str(i + 1) + '/' + str(len(images)) + ']', end='')
        i += 1
    if i == len(images):
        pt = filePath.replace('$PNAME', Manga['name']).replace('$CP', parseChapter(chapter)).replace('$PROV', 'kissmanga').replace('$LANG', 'en')
        if ext == 'PDF': saveAsPDF(pt.replace('$EXT', 'pdf'))
        elif ext == 'CBZ': saveAsCBZ(pt.replace('$EXT', 'cbz'))

        print('\rSuccesfully Downloaded ' + Manga['name'] + ' ' + chapter + ' with ' + str(len(images)) + ' pages and saved as ' + ext + ' in ' + str(timedelta(seconds=round(time.time() - start))))
        providers['kissmanga']['mangas'][manga]['chapters'][chapter] = True
        with open(providersFile, 'w') as outfile: json.dump(providers, outfile, indent=4)
    else: print('\rError Downloading, missing pages.')

def saveAsPDF(pt):
    images = []
    for file in glob('./images/*.jpg'):
        img = Image.open(fname)
        if img.mode != 'RGB': img = img.convert('RGB')
        images.append(img)
    
    if not path.exists(pt.rpartition('/')[0]): call(['mkdir', pt.rpartition('/')[0]])
    img = images.pop(0)
    img.save(pt, "PDF" ,resolution=100.0, save_all=True, append_images=images)
    call(['rm', './images', '-r'])

def saveAsCBZ(pt):
    if not path.exists(pt.rpartition('/')[0]): call(['mkdir', pt.rpartition('/')[0]])
    zipObj = ZipFile(pt, 'w')
    for file in glob('./images/*.jpg'): zipObj.write(file, file.rpartition('/')[2])
    zipObj.close()
    call(['rm', './images', '-r'])

def downloadMissing():
        for manga in Mangas:
            for chapter in manga['chapters']:
                if not chapter['downloaded']: 
                    if provider == 'submanga': downloadChapterSubmanga(manga, chapter, 'CBZ')
                    elif provider == 'kissmanga': downloadChapterKissmanga(manga, chapter, 'CBZ')

def downloadAll():
    for provider in providers:
        for manga in providers[provider]['mangas']:
            for chapter in providers[provider]['mangas'][manga]['chapters']: downloadChapter(provider, manga, chapter)

def refreshChapters():
    for manga in Mangas:
            soup = BeautifulSoup(requests.get(providers[manga['provider']]['chaptersUrl'].replace('$ID', manga['id'])).text, "html.parser")
            if manga['provider'] == 0:
                for cp in reversed(soup.select("div.capitulos-list a")):
                    cpid = cp['href'].rpartition('/')[2]
                    if 'special' in cpid:
                        manga['specials'] = manga['specials'] + 1
                        cpname = 'Special: ' + str(manga['specials'])
                    else: 
                        cpname = cpid.replace('%20', '')
                        match = re.findall(r'\d[\dv\.]*', cpname)
                        if len(match) > 0: cpname = match[0][:-1] if match[0][-1] == '.' else match[0]
                        cpname = cpname.replace('.v', 'v').zfill(5)
                        if 'v' in cpname:
                            pr = cpname.partition('v')
                            cpname = pr[0].zfill(4) + 'v' + pr[2]
                    if not any(cpname == cp['name'] for cp in manga['chapters']): manga['chapters'].append({
                        'id': cpid,
                        'name': cpname,
                        'number': len(manga['chapters']),
                        'downloaded': False
                    })
            elif manga['provider'] == 1:
                for cp in reversed(soup.select('div.listing a')):
                    cpname = re.findall(': ([^<]*)', cp.text)[0]
                    cpid = cp['href'].rpartition('_')[2]
                    if not any(cpname == cp['name'] for cp in manga['chapters']): manga['chapters'].append({
                        'id': cpid,
                        'name': cpid.zfill(4) + ' - ' + cpname,
                        'downloaded': False
                    })
    with open(providersFile, 'w') as outfile: json.dump(Mangas, outfile, indent=4)

def addManga():
    # Select Provider
    for index, provider in enumerate(providers): print(index,'-', provider['id'])
    provider = int(input('Select Provider: '))

    # Select ID
    id = input('ID (kimetsu-no-yaiba, 45648): ')
    while requests.get(providers[provider]['chaptersUrl'].replace('$ID', id)).status_code != 200:
        print('ID: "' + id + '" not found in provider ' + provider)
        id = input("ID (kimetsu-no-yaiba, 45648): ")
    
    if not any([mg['provider'] == provider and mg['id'] == id for mg in Mangas]):
        aniidQuery = '''
            query ($search: String) {
                Media(search: $search, type: MANGA) {
                    id
                    title {
                        romaji
                        english
                    }
                    description
                    genres
                    coverImage {extraLarge}
                    startDate {
                        year
                        month
                        day
                    }
                    staff {
                        edges {
                            role
                            node {name{full}}
                        }
                    }
                }
            }
        '''
        url = 'https://graphql.anilist.co'

        # Download metadata from anilist
        inp = input('\rAnime name (Kimetsu No Yaiba): ')
        response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': inp}})
        while True:
            info = response.json()
            if response.status_code == 200 and info['data']['Media'] is not None:
                info = info['data']['Media']
                inp = 'e'
                nm = info['title']['romaji'] if 'romaji' in info['title'] else info['title']['english']
                while inp != 'y' and inp != 'n' and inp != '':
                    inp = input('\rFound manga "' + nm + '" on anilist with id: ' + str(info['id']) + ', is this ok? (y/n): ')
                
                if inp != 'n':
                    # Select Path
                    defaultPT = rootpt + nm
                    pt = input('Path to save files (def: ' + defaultPT + '): ')
                    if len(pt) == 0: pt = defaultPT
                    while not path.exists(pt.rpartition('/')[0]):
                        pt = input('Parent folder does not exist, enter new path: ')
                    if not path.exists(pt): call(['mkdir', pt])

                    writers = []
                    artists = []

                    for staff in info['staff']['edges']:
                        if 'Art' in staff['role']: artists.append(staff['node']['name']['full'])
                        if 'Story' in staff['role']: writers.append(staff['node']['name']['full'])
                    
                    # Download cover image
                    downloadImage(info['coverImage']['extraLarge'], pt + '/cover.jpg', 3, 0.1)
                    Mangas.append({
                        'name': nm,
                        'id': id,
                        'provider': provider,
                        'path': pt,
                        'anilistID': info['id'],
                        'description': info['description'],
                        'startDate': info['startDate'],
                        'genres': info['genres'],
                        'staff': {
                            'writers': writers,
                            'artists': artists,
                        },
                        'specials': 0,
                        'chapters': {}
                    })
                    
                    return refreshChapters()
                else:
                    search = input('Enter new search terms: ')
                    response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': search}})
            else:
                search = input('Failed to load manga, enter new search terms: ')
                response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': search}})
    else: print('Anime was already monitored')

def syncMissing():
    for provider in providers:
        for manga in providers[provider]['mangas']:
            Manga = providers[provider]['mangas'][manga]
            pt = filePath.replace('$PNAME', Manga['name']).replace('$PROV', provider).replace('$LANG', providers[provider]['language'])
            for chapter in Manga['chapters']:
                pth = pt.replace('$CP', parseChapter(chapter))
                providers[provider]['mangas'][manga]['chapters'][chapter] = path.exists(pth.replace('$EXT', 'pdf')) or path.exists(pth.replace('$EXT', 'cbz'))
    with open(providersFile, 'w') as outfile: json.dump(providers, outfile, indent=4)

if '-a' == sys.argv[1]: addManga()
if '-r' == sys.argv[1]: refreshChapters()
if '-d' == sys.argv[1]: downloadMissing()
if '-D' == sys.argv[1]: downloadAll()
if '-s' == sys.argv[1]: syncMissing()