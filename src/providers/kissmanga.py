import requests
import re

# TODO add last chapter to list
# Returns all mangas urls and name in a tuple
def search(name):
    req = requests.get(f"https://kissmanga.org/manga_list?q={name.replace(' ', '+')}&action=search")
    
    if req.status_code != 200: 
        return []
    
    return list(map(lambda m: {"name": m[1], "url": m[0], 'language': 'English', 'provider': 'kissmanga'}, re.findall(r'<a class="item_movies_link" href="([^"]+)">([^"]+)<\/a>', str(req.content))))

# Returns all chapters url and name in a tuple
def chapters(url):
    req = requests.get(f"https://kissmanga.org{url}")

    if req.status_code != 200: 
        return []
    results = re.findall(r'<h3>[^<]*<a href="([^"]+\/chapter[_-]([\d\.]+))"\n*\s*[^>]*>([^<]+)<', str(req.content))
    return list(map(lambda c: {"name": parseName(c[2]).strip(), "url": c[0], "number": c[1]}, results)) 

def parseName(name):
    if "\\n" not in name:
        return name
    elif ":" not in name:
        return name.split("\\n")[1]
    else:
        return name.split("\\n")[1].split(":")[1]

# Returns a collection of urls of panels
def get(url):
    req = requests.get(f"https://kissmanga.org{url}")

    if req.status_code != 200: 
        return []
    return re.findall(r'<img src="(https:[^"]+)"', str(req.content))
