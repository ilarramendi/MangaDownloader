import requests
import json
from re import findall, escape

def search(name):
    ret = []
    req = requests.post('https://manganato.com/getstorysearchjson', data={'searchword': name})
    if req.status_code == 200:
        for item in req.json():
            ret.append({
                'name': ''.join(findall(r'([^>]+)(?:(?:<[^>]+>)|$)', item['name'])),
                'chapters': item['lastchapter'],
                'url': item['link_story'],
                'provider': 'manganato',
                'language': 'English'
            })
    return ret

# TODO add the other image server
def chapters(url):
    req = requests.get(url)
    ret = []
    if req.status_code == 200:
        for item in findall(f'href="({escape(url)}\/chapter-([\d\.]+))" title="[^"]+: ([^"]+)"', req.text):
            ret.append({
                'url': item[0],
                'number': item[1],
                'name': item[2]
            })
    return ret

def get(url):
    req = requests.get(url)
    return findall(r'img src="([^"]+)" alt="[^"]+page', req.text) if req.status_code == 200 else []

    