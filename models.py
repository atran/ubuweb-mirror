# for download_alternate_work function
from __future__ import unicode_literals
import youtube_dl
# https://realpython.com/beautiful-soup-web-scraper-python/
# data object stuff
from dataclasses import dataclass, field
# URL and scraping stuff
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
# Progress bar
from tqdm import tqdm
# file utils
from os.path import exists
# custom constants
from constants import *
# Javascript rendering
from requests_html import HTMLSession

@dataclass
class Artist:
    name: str = ""
    url: str = ""
    id: int = None
    description: str = ""
    born: int = None
    broken: bool = False
    dmca: bool = False

@dataclass
class Work:
    name: str = ""
    daterange: int = ""
    description: str = None
    url: str = None
    download_url: str = None
    artist = None

    def set_download_url(self, work):
        # TODO remove work object as a thing to pass in, it's redundant
        page = requests.get(work.url)
        soup = BeautifulSoup(page.content, "html.parser")
        video = soup.find("div", class_="ubucontainer")
        if video is not None:
            moviename = video.find("a", id="moviename") 
            if moviename is not None:
                self.download_url = BASE_FILM_URL + moviename["href"]
            else:
                print("reload and run with a dynamic scraper. Link might be javascript")
                session = HTMLSession()
                response = session.get(work.url)
                response.html.render()
                moviename = response.html.find("#moviename") 
                self.download_url = BASE_FILM_URL + moviename[0].attrs["href"]
        return work

    def download_alternate_work(self):
        page = requests.get(self.url)
        soup = BeautifulSoup(page.content, "html.parser")
        video = soup.find("div", class_="ubucontainer")
        iframe = video.find("iframe")
        if iframe is None:
            print("iframe is absent. Try dynamic scraper")
            session = HTMLSession()
            response = session.get(self.url)
            response.html.render()
            elem = response.html.find("iframe") 
            iframe = elem[0].attrs
        output_template = DOWNLOAD_PATH + "%(title)s.%(ext)s"
        ydl_opts = {"outtmpl" : output_template}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([iframe["src"]])

    def download_work(self):
        response = requests.get(self.download_url, stream=True)
        if response.url != ERROR_URL:
            url_parts = urlparse(self.download_url)
            path = url_parts.path.split("/")
            filename = DOWNLOAD_PATH + path[-1:][0]
            print(filename)
            # copypasta https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests
            size_in_bytes = int(response.headers.get('content-length', 0))
            block_size = 1024
            progress_bar = tqdm(total=size_in_bytes, unit='iB', unit_scale=True)
            if exists(filename) is False:
                with open(filename, "wb") as file:
                    for data in response.iter_content(block_size):
                        progress_bar.update(len(data))
                        file.write(data)
                progress_bar.close()
            else:
                print('file exists, write a function to check for partial downloads')
        else:
            print("whoopsy daisy, no local download, need alternate download function")
            self.download_alternate_work()

class Page:
    def get_tables(self, page):
        soup = BeautifulSoup(page.content, "html.parser")
        tables = soup.find_all("table")
        return tables

    # refactor this and get_links to reuse the response for many functions
    def get_artist_description(self, url):
        page = requests.get(url)
        tables = self.get_tables(page)
        storycontent = tables[1].find("div", class_="storycontent")
        description = storycontent.find_all("p")
        return description

    def get_links(self, url):
        page = requests.get(url)
        if page.url != ERROR_URL:
            tables = self.get_tables(page)
            links = tables[1].find_all("a")
            return links
        else:
            print(f"server redirected to {ERROR_URL}")
            return ERROR_URL

    def get_artists(self, url):
        # refactor to only do one request, not two
        links = self.get_links(url)
        # description = self.get_artist_description(url)
        artists = []
        for artist in links:
            a = Artist()
            a.name = artist.text.strip() 
            a.url = BASE_FILM_URL + artist["href"]
            # a.description = description
            artists.append(a)
        # this convention removes the left nav bar links.
        artists.pop(0)
        return artists

    def get_artist_works(self, artist):
        links = self.get_links(artist.url)
        works = []
        for work in links:
            w = Work()
            w.name = work.text.strip()
            w.url = BASE_FILM_URL + work["href"]
            w.artist = artist
            works.append(w)
        # this convention removes the left nav bar links.
        for _ in range(2):
            works.pop(0)
        return works
