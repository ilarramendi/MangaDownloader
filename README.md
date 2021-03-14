# Manga-Downloader
Tool to automaticaly download manga and metadata, all suggestions are welcome :)

Supported output files are .PDF and .CBZ

Metadata is saved as ComicInfo.xml inside .CBZ files, this is intended to work with [Komga](https://komga.org/)

# Functionality
- [x] Search for mangas in providers
- [x] Automaticaly download all chapters from all mangas
- [x] Monitor for new releses (cron job with -d)
- [x] Automatic metadata and cover image downloading from Anilist
- [ ] Episode name downloading (only supported with kissmanga, need a place to find them other than the providers)
- [ ] Removing of ugly first pages added by translators
- [ ] Individual chapter downloading
- [ ] Individual manga downloading

# Important !!
Please dont set the delay to a very low value, this will hammer the providers servers (be nice :)), recommended value is 1.

# Run options
* -d --> Download all missing chapters from all series
* -D --> Download all chapters again
* -a --> Add new manga (guided)
* -r --> Refresh missing chapters for all series
* -s --> Sync missing chapters from disk




# Providers:
* Submanga (ES)
* Kissmanga (EN)
