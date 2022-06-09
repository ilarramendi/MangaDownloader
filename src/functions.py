import requests
import shutil
import os
from zipfile import ZipFile
from glob import glob
from time import sleep
import lxml.etree as ET

import providers.kissmanga
import providers.manganato

providers = {'kissmanga': providers.kissmanga, 'manganato': providers.manganato}

BASE_PATH = '/media/e/manga'

def add():
    name = ''
    while len(name) == 0:
        print('Manga name: ', end='')
        name = input()
    
    server = "-1"
    while not server.isdigit() or int(server) < 0 or int(server) > 2:
        for i, p in enumerate(providers):
            print(f"{i}: {p}")
        server = input('Select server: ')
    server = list(providers.keys())[int(server)]
    
    mangas = providers[server].search(name)  
    length = len(str(len(mangas)))
    for i, manga in enumerate(mangas):
        print(f"{str(i).zfill(length)}: {manga['name']}")

    manga = "-1"
    while not manga.isdigit() or int(manga) < 0 or int(manga) > len(mangas):
        manga = input('Select manga number (ctrl + c to exit): ')

    manga = mangas[int(manga)]
    if not updateAniiList(manga): return False

    manga['path'] = f"{BASE_PATH}/{manga['name'].replace('/', '-')} ({manga['startDate']['year']}) [{manga['provider']}]"
    inp = input(f"Select path ({manga['path']}): ")
    if inp != '': manga['path'] = inp

    manga['chapters'] = providers[server].chapters(manga['url'])

    return manga

def download(manga):
    if os.path.isdir("./chapter"): shutil.rmtree("./chapter")
    if not os.path.isdir(manga['path']): os.mkdir(manga['path'])
    if not os.path.exists(manga['path'] + '/poster.jpg'): downloadImage(manga['path'] + '/poster.jpg', manga['cover'])

    for i, chapter in enumerate(reversed(manga['chapters'])):
        out = f"{manga['path']}/[{chapter['number']}] {chapter['name'].replace('/', '-')}.cbz"
        if os.path.isfile(out): continue
        
        os.mkdir("./chapter")

        for j, image in enumerate(providers[manga['provider']].get(chapter['url'])):
            if not downloadImage(f"./chapter/panel-{j}.jpg", image): 
                print(f"Failed to download: {manga['name']} ({chapter['number']}): {chapter['name']}")
                break
        else:
            geterateComicInfo(chapter, manga)
            saveCBZ(out)
            print(f"Downloaded: {manga['name']} ({chapter['number']}): {chapter['name']}")

        shutil.rmtree("./chapter")

# Todo make a custom method to stop using ET
def geterateComicInfo(chapter, manga):
    root = ET.Element("ComicInfo")
    root.text = '\n\t'
    b1 = ET.SubElement(root, "Title") 
    b1.text = chapter['name']
    b1 = ET.SubElement(root, "Number") 
    b1.text = str(chapter['number'])
    b1 = ET.SubElement(root, "Summary") 
    b1.text = manga['description']
    b1 = ET.SubElement(root, "Year") 
    b1.text = str(manga['startDate']['year'])
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

    with open ('./chapter/ComicInfo.xml', "wb") as f: 
        ET.ElementTree(root).write(f)

def writeComicInfo(info):
    str = '<ComicInfo>\n'
    for property in info:
        str += f"\t<{property}>{info[property]}</{property}>\n"
    str += '</ComicInfo>'

    with open('./chapter/ComicInfo.xml', 'w') as f:
        f.write(str)

def saveCBZ(pt):
    zipObj = ZipFile(pt, 'w')
    for file in glob('./chapter/*'):
        zipObj.write(file, file.rpartition('/')[2])
    zipObj.close()

def downloadImage(output, url):
    i = 0
    while i < 5:
        try:
            # TODO only add headers if needed
            res = requests.get(url, stream=True, timeout=10, headers={'Referer': 'https://readmanganato.com/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'})
            if res.status_code == 200:
                with open(output ,'wb') as f:
                    shutil.copyfileobj(res.raw, f)
                return True
            i += 1
        except: pass
        sleep(3 * i)
    print(f"failed to download: {url}")
    return False

def updateAniiList(manga):
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

    search = manga['name']

    while True:
        response = requests.post(url, json={'query': aniidQuery, 'variables': {'search': search}})
        info = response.json()

        if response.status_code == 200 and info['data']['Media'] is not None:
            info = info['data']['Media']
            title = info['title']['romaji'] if 'romaji' in info['title'] else info['title']['english']
            inp = input(f'\rFound manga "{title}" on anilist with id: {info["id"]}, This looks ok? (y)/n: ')
            if inp == 'n': return False

            manga['name'] = title
            manga['description'] = info['description']
            manga['genres'] = info['genres']
            manga['startDate'] = info['startDate']
            manga['staff'] = {'writers': [], 'artists': []}
            manga['id'] = info['id']
            manga['cover'] = info['coverImage']['extraLarge']
            
            for staff in info['staff']['edges']:
                if 'Art' in staff['role'] or 'Story & Art' in staff['role']:
                    manga['staff']['artists'].append(staff['node']['name']['full'])
                if 'Story' in staff['role'] or 'Story & Art' in staff['role']:
                    manga['staff']['writers'].append(staff['node']['name']['full'])
            return manga
        else: 
            search = input('Manga not found, enter new search term: ')

