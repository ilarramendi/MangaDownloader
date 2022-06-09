'''
LifeCicle:

start in add -> ask for manga name -> ask for server to download -> select from manga list -> select on metadata provider -> done
start in download -> download show in parameter -d or all if -D

'''

# TODO make the script easy to kill

from functions import add, download
import json
from os.path import isfile
from sys import argv

try:
    with open("mangas.json", "rb") as file:
        mangas = json.load(file)
except:
    mangas = []

if '-a' in argv: 
    manga = add()
    if manga: mangas.append(manga)
elif '-d' in argv:
    for i, manga in enumerate(mangas):
        print(f"{i}: {manga['name']} [{manga['provider']}]")
    download(mangas[int(input())])

with open("mangas.json", "w") as file:
    json.dump(mangas, file, sort_keys=True, indent=2)

