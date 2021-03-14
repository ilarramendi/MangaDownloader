import requests
from time import sleep
from PIL import Image, ImageFile
from subprocess import call
from glob import glob
from os import path
from shutil import rmtree
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
import sys
import time
from datetime import timedelta, datetime
from zipfile import ZipFile
import lxml.etree as ET


ImageFile.LOAD_TRUNCATED_IMAGES = True

delay = 1 / 2
mangasFile = './mangas.json'
logFile = './MangaDownloader.log'
rootpt = '/media/e/manga/'
Mangas = []
Numlength = 4
providers = [
        {
            'id': 'submanga',
            "imageUrl": "https://submanga.io/uploads/manga/$ID/chapters/$CHAPTER/$IMG.jpg",
            "chaptersUrl": "https://submanga.io/manga/$ID",
            "pagesUrl": "https://submanga.io/manga/$ID/$CHAPTER",
            "searchUrl": "https://submanga.io/search?query=$SEARCH",
            "defaultLang": 'es'
        }
        ,{
            'id': 'kissmanga',
            "imageUrl": "https://kissmanga.org/chapter/$ID/chapter_$CHAPTER",
            "chaptersUrl": "https://kissmanga.org/manga/$ID",
            "searchUrl": "https://kissmanga.org/manga_list?q=$SEARCH&action=search",
            "defaultLang": 'en'
        }
    ]

if path.exists(mangasFile):
    with open(mangasFile, 'r') as json_file:
        Mangas = json.load(json_file)

def parseChapterNumber(cp):
    cp = cp.replace('.v', ' v')
    info = cp.partition('.')
    return info[0].zfill(Numlength) + info[1] + info[2]

def logText(text = '', newLine = True, error = False, success = False, warn = False, bold = False, ul = False):
    out = (datetime.now().strftime("[%m/%d/%Y %H:%M:%S] --> ") + text) if text != '' else ''
    if newLine:
        with open(logFile, 'a') as log: log.write(out + '\n')

    if bold: out = '\033[1m' + out + '\033[0m'
    if ul: out = '\033[4m' + out + '\033[0m'
    if error: out = '\033[91m' + out + '\033[0m'
    elif success: out = '\033[92m' + out + '\033[0m'
    elif warn: out = '\033[93m' + out + '\033[0m'

    print('\r\033[K' + out, end='\n' if newLine else '')

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
        logText('Failed to download: ' + url, error = True)
        return False

def downloadChapterSubmanga(manga, chapter, ext):
    start = time.time()
    imgUrl = providers[0]['imageUrl'].replace('$ID', manga['id']).replace('$CHAPTER', chapter['id'])
    if path.exists('./manga'): rmtree('./manga')
    call(['mkdir', './manga'])

    #Get # of pages
    pages = int(BeautifulSoup(requests.get(providers[0]['pagesUrl'].replace('$ID', manga['id']).replace('$CHAPTER', chapter['id'])).text, "html.parser").select("select.selectpicker option")[-1].text)

    useZero = requests.get(imgUrl.replace('$IMG', '01')).status_code == 200
    i = 1
    start2 = time.time()
    while i < pages and downloadImage(imgUrl.replace('$IMG', str(i).zfill(2) if useZero else str(i)), "./manga/" + str(i).zfill(4) + '.jpg', 3, delay):
        logText('Succesfully downloaded ' + manga['name'] + ' ' + chapter['name'] + ' page [' + str(i) + '/' + str(pages) + ']', newLine = False)
        start2 = time.time()
        i += 1

    if i == pages:
        pt = manga['path'] + '/' + manga['name'] + ' - ' + chapter['name'] + ' [submanga] [' + manga['language'] + '].' + ext.lower() 
        if ext == 'PDF': saveAsPDF(pt)
        else: 
            createComicInfo(manga, chapter)
            saveAsCBZ(pt)

        logText('Succesfully Downloaded ' + manga['name'] + ' ' + chapter['name'] + ' with ' + str(i) + ' pages and saved as ' + ext + ' in ' + str(timedelta(seconds=round(time.time() - start))), success = True)
        Mangas[Mangas.index(manga)]['chapters'][manga['chapters'].index(chapter)]['downloaded'] = True
        with open(mangasFile, 'w') as outfile: json.dump(Mangas, outfile, indent=4)
    else: logText('Error Downloading, missing pages.', error = True)

def downloadChapterKissmanga(manga, chapter, ext):
    start = time.time()
    if path.exists('./manga'): rmtree('./manga')
    call(['mkdir', './manga'])
    images = BeautifulSoup(requests.get(providers[1]['imageUrl'].replace('$ID', manga['id']).replace('$CHAPTER', chapter['id'])).text, "html.parser").select("div#centerDivVideo img")
    i = 0
    while i < len(images) and downloadImage(images[i]['src'], './manga/' + str(i).zfill(4) + '.jpg', 3, delay):
        logText('Succesfully downloaded ' + manga['name'] + ' ' + chapter['name'] + ' page [' + str(i + 1) + '/' + str(len(images)) + ']', newLine = False)
        i += 1
    if i == len(images):
        pt = manga['path'] + '/' + manga['name'] + ' - ' + chapter['name'] + ' [kissmanga] [' + manga['language'] + '].' + ext.lower() 
        if ext == 'PDF': saveAsPDF(pt)
        else: 
            createComicInfo(manga, chapter)
            saveAsCBZ(pt)

        logText('Succesfully Downloaded ' + manga['name'] + ' ' + chapter['name'] + ' with ' + str(len(images)) + ' pages and saved as ' + ext + ' in ' + str(timedelta(seconds=round(time.time() - start))), success = True)
        Mangas[Mangas.index(manga)]['chapters'][manga['chapters'].index(chapter)]['downloaded'] = True
        with open(mangasFile, 'w') as outfile: json.dump(Mangas, outfile, indent=4)
    else: logText('Error Downloading, missing pages.', error = True)

def search(stri, provider):
    req = requests.get(providers[provider]['searchUrl'].replace('$SEARCH', stri.replace(' ', '+')))
    
    if req.status_code != 200: return []
    if provider == 0:
        req = req.json()
        if 'suggestions' in req: return [[mg['value'], mg['data']] for mg in req['suggestions']]
        else: return []
    else: return [[mg.text, mg['href'].rpartition('/')[2]] for mg in BeautifulSoup(req.text, "html.parser").select('a.item_movies_link')][0:15]

def saveAsPDF(pt):
    images = []
    for file in glob('./manga/*.jpg'):
        img = Image.open(fname)
        if img.mode != 'RGB': img = img.convert('RGB')
        images.append(img)
    
    if not path.exists(pt.rpartition('/')[0]): call(['mkdir', pt.rpartition('/')[0]])
    img = images.pop(0)
    img.save(pt, "PDF" ,resolution=100.0, save_all=True, append_images=images)

def createComicInfo(manga, chapter):
    root = ET.Element("ComicInfo")
    root.text = '\n\t'
    b1 = ET.SubElement(root, "Title") 
    b1.text = chapter['name']
    b1 = ET.SubElement(root, "Series") 
    b1.text = manga['name']
    b1 = ET.SubElement(root, "Number") 
    b1.text = str(chapter['number'])
    b1 = ET.SubElement(root, "Summary") 
    b1.text = manga['description']
    b1 = ET.SubElement(root, "Year") 
    b1.text = str(manga['startDate']['year'])
    b1 = ET.SubElement(root, "Month") 
    b1.text = str(manga['startDate']['month'])
    b1 = ET.SubElement(root, "Day") 
    b1.text = str(manga['startDate']['day'])
    b1 = ET.SubElement(root, "Writer") 
    b1.text = ','.join(manga['staff']['writers'])
    b1 = ET.SubElement(root, "Penciller") 
    b1.text = ','.join(manga['staff']['artists'])
    b1 = ET.SubElement(root, "anilistID") 
    b1.text = str(manga['id'])
    b1 = ET.SubElement(root, "Genre") 
    b1.text = ','.join(manga['genres'])
    b1 = ET.SubElement(root, "LanguageISO") 
    b1.text = manga['language']

    for d in root:
        d.tail = '\n\t'
    root[-1].tail = '\n'

    with open ('./manga/ComicInfo.xml', "wb") as files : 
        ET.ElementTree(root) .write(files)

def saveAsCBZ(pt):
    if not path.exists(pt.rpartition('/')[0]): call(['mkdir', pt.rpartition('/')[0]])
    zipObj = ZipFile(pt, 'w')
    for file in glob('./manga/*'): zipObj.write(file, file.rpartition('/')[2])
    zipObj.close()

def downloadMissing():
        for manga in Mangas:
            for chapter in manga['chapters']:
                if not chapter['downloaded']: 
                    if manga['provider'] == 0: downloadChapterSubmanga(manga, chapter, 'CBZ')
                    else: downloadChapterKissmanga(manga, chapter, 'CBZ')

def downloadAll():
    for provider in providers:
        for manga in providers[provider]['mangas']:
            for chapter in providers[provider]['mangas'][manga]['chapters']: downloadChapter(provider, manga, chapter)

def getChapters(id, provider):
    soup = BeautifulSoup(requests.get(providers[provider]['chaptersUrl'].replace('$ID', id)).text, "html.parser")
    res = []
    if provider == 0:
        specials = 0
        for cp in reversed(soup.select("div.capitulos-list a")):
            cpid = cp['href'].rpartition('/')[2]
            if 'special' in cpid:
                specials += 1
                cpname = 'Special: ' + str(specials).zfill(3)
            else:
                cpname = cpid.replace('%20', '')
                match = re.findall(r'\d[\dv\.]*', cpname)
                if len(match) > 0: cpname = match[0][:-1] if match[0][-1] == '.' else match[0]
                cpname = cpname.replace('.v', 'v').zfill(Numlength)
                if 'v' in cpname:
                    pr = cpname.partition('v')
                    cpname = pr[0].zfill(Numlength) + 'v' + pr[2]
                elif '.' in cpname:
                    pr = cpname.partition('.')
                    cpname = pr[0].zfill(Numlength) + '.' + pr[2]    
            res.append({
                'id': cpid,
                'name': cpname.encode("ascii", "ignore").decode(),
                'number': len(res),
                'downloaded': False
            })
    elif provider == 1:
        for cp in reversed(soup.select('div.listing a')):
            cpid = parseChapterNumber(cp['href'].rpartition('_')[2])
            cpname = cpid + ' - ' + cp.text.partition(': ')[2].replace('\\', '') if ':' in cp.text else cpid
            res.append({
                'id': cpid,
                'name': cpname.encode("ascii", "ignore").decode(),
                'number': cpid,
                'downloaded': False
            })
    return res

def addManga():
    # region Provider
    for index, provider in enumerate(providers): print(index,'-', provider['id'])
    provider = int(input('Select Provider: '))
    # endregion

    # region Provider ID
    mgID = -1
    mgName = ''
    cps = []
    while mgID == -1:
        inp = input('\rManga name (kimetsu no yaiba): ')
        res =  search(inp, provider)
        if len(res) > 0:
            print('0 - Try Again')
            for index, mg in enumerate(res):
                print(index + 1, '-', mg[0])
            inp = input('Select the correct manga (1): ')
            inp = 1 if inp == '' else int(inp)
            if inp > 0:
                mgID = res[inp - 1][1]
                mgName = res[inp - 1][0]
                cps = getChapters(mgID, provider)
                inp = input('The latest released chapter of this manga is: "' + cps[-1]['name'] + '" and has ' + str(len(cps)) + ' chapters , This looks ok? (y/n): ')
                if inp != 'y' and inp != '': mgID = -1
                if any([mg['path'] == provider and mg['id'] == mgID for mg in Mangas]):
                    inp = input('Manga was already monitored, add anyway? (y/n): ')
                    if inp != 'y' and inp != '': mgID = -1
        else: print('No results found, try again')
    # endregion
    
    # region anilist
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

    response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': mgName}})
    info = response.json()
    while True:
        if response.status_code == 200 and info['data']['Media'] is not None:
            info = info['data']['Media']
            nm = info['title']['romaji'] if 'romaji' in info['title'] else info['title']['english']
            inp = input('\rFound manga "' + nm + '" on anilist with id: ' + str(info['id']) + ', This looks ok? (y/n): ')
            
            if inp == 'y' or inp == '': break
        else: print('Manga not found')
        response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': input('Enter new search terms: ')}})
        info = response.json()

    writers = []
    artists = []

    for staff in info['staff']['edges']:
        if 'Art' in staff['role']: artists.append(staff['node']['name']['full'])
        if 'Story' in staff['role']: writers.append(staff['node']['name']['full'])
    # endregion

    # region Language
    lang = input('Select Language (' + providers[provider]['defaultLang'] + "): ")
    if lang == '': lang = providers[provider]['defaultLang']
    # endregion

    #region Path
    defaultPT = rootpt + nm + ' (' + lang + ')'
    pt = input('Path to save files (' + defaultPT + '): ')
    if len(pt) == 0: pt = defaultPT
    while not path.exists(pt.rpartition('/')[0]): pt = input('Parent folder does not exist, enter new path: ')
    if not path.exists(pt): call(['mkdir', pt])
    #endregion 

    downloadImage(info['coverImage']['extraLarge'], pt + '/cover.jpg', 3, 0.5)
    Mangas.append({
        'name': nm,
        'id': mgID,
        'provider': provider,
        'path': pt,
        'anilistID': info['id'],
        'description': info['description'].replace('<br>', '').encode("ascii", "ignore").decode(),
        'startDate': info['startDate'],
        'genres': info['genres'],
        'language': lang,
        'staff': {
            'writers': writers,
            'artists': artists,
        },
        'specials': 0,
        'chapters': cps
    })
    logText('Succesfully added ' + nm + ' (' + lang + ') from provider ' + providers[provider]['id'] + ' with ' + str(len(cps)) + ' chapters.', success = True)
    with open(mangasFile, 'w') as outfile: json.dump(Mangas, outfile, indent=4)

def syncMissing():
    for provider in providers:
        for manga in providers[provider]['mangas']:
            Manga = providers[provider]['mangas'][manga]
            pt = filePath.replace('$PNAME', Manga['name']).replace('$PROV', provider).replace('$LANG', providers[provider]['language'])
            for chapter in Manga['chapters']:
                pth = pt.replace('$CP', parseChapter(chapter))
                providers[provider]['mangas'][manga]['chapters'][chapter] = path.exists(pth.replace('$EXT', 'pdf')) or path.exists(pth.replace('$EXT', 'cbz'))
    with open(mangasFile, 'w') as outfile: json.dump(providers, outfile, indent=4)

if '-a' == sys.argv[1]: addManga()
if '-r' == sys.argv[1]: getChapters()
if '-d' == sys.argv[1]: downloadMissing()
if '-D' == sys.argv[1]: downloadAll()
if '-s' == sys.argv[1]: syncMissing()