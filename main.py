# custom data models
from models import Page
import random
from constants import *
import logging
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(message)s",
                    filename="transfers.log",
                    filemode="a"
        )

def download_random_work_from(artists):
    page = Page()
    r = len(artists)
    artist = artists[random.choice(range(r))]
    logging.debug(f"Artist is: {print(artist)}")
    artist_works = page.get_artist_works(artist)
    r = len(artist_works)
    work = artist_works[random.choice(range(r))]
    work.download_work()

def download_all_works_from(artist):
    page = Page()
    artist_works = page.get_artist_works(artist)
    for work in artist_works:
        work.download_work()

def download_all_works_parallel_from(artist):
    page = Page()
    artist_works = page.get_artist_works(artist)
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(lambda work: work.download_work(), artist_works)

def main():
    page = Page()
    artists_page = page.get_artists(FILM_URL)
    for artist in artists_page:
        try:
            download_all_works_parallel_from(artist)
        except Exception as e:
            logging.error("Downloading work failed", exc_info=True)
    # r = len(artists_page)
    # download_all_works_from(artists_page[random.choice(range(r))])

if __name__ == "__main__":
    main()
