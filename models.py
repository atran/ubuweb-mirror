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
import logging
from os import makedirs
import time

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
    artist: Artist = None

    def __post_init__(self):
        """
        Automatically set the download URL when the Work object is initialized.
        """
        self.set_download_url()

    def set_download_url(self):
        """
        Set the download URL for the work by parsing the HTML or using a dynamic scraper.
        """
        # Fetch the page content
        try:
            page = requests.get(self.url, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, "html.parser")

            # Try to find the video container
            video = soup.find("div", class_="ubucontainer")
            if video is not None:
                moviename = video.find("a", id="moviename")
                if (moviename is not None):
                    self.download_url = BASE_FILM_URL + moviename["href"]
                else:
                    logging.info("Reload URL and run with a dynamic scraper. Link might be javascript")
                    session = HTMLSession()
                    response = session.get(self.url)
                    response.html.render()
                    moviename = response.html.find("#moviename")
                    self.download_url = BASE_FILM_URL + moviename[0].attrs["href"]
        except Exception as e:
            logging.error(f"Failed to set download URL for {self.name}")

    def download_alternate_work(self):
        """
        Download alternate work using iframe or dynamic scraping.
        """
        # Fetch the page content
        try:
            page = requests.get(self.url, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, "html.parser")

            # Try to find the iframe
            video = soup.find("div", class_="ubucontainer")
            iframe = video.find("iframe") if video else None

            # Fallback to dynamic scraping if iframe is not found
            if not iframe:
                logging.info("Falling back to dynamic scraper for iframe content.")
                session = HTMLSession()
                response = session.get(self.url)
                response.html.render()
                iframe_elem = response.html.find("iframe")
                iframe = iframe_elem[0].attrs if iframe_elem else None

            # Download the video using youtube-dl
            if iframe and "src" in iframe:
                output_template = os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s")
                ydl_opts = {"outtmpl": output_template}
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([iframe["src"]])
            else:
                logging.warning(f"No iframe found for alternate work: {self.name}")
        except Exception as e:
            logging.error(f"Failed to download alternate work: {self.name}", exc_info=True)

    def download_work(self):
        """
        Download the work's HTML and video, saving them in the appropriate folder structure.
        """
        # Save the work HTML
        try:
            page = requests.get(self.url, timeout=10)
            page.raise_for_status()
            artist_name = self.artist.name.replace(" ", "_")
            work_name = self.name.replace(" ", "_")
            Page().save_html(self.url, page.text, artist_name=artist_name, work_name=work_name)

            # Download the video
            response = requests.get(self.download_url, stream=True, timeout=10)
            response.raise_for_status()

            # Parse the URL to extract the video filename
            url_parts = urlparse(self.download_url)
            video_filename = os.path.basename(url_parts.path)

            # Construct the directory and file path
            directory = os.path.join(DOWNLOAD_PATH, artist_name, work_name)
            filepath = os.path.join(directory, video_filename)

            # Ensure the directory exists
            makedirs(directory, exist_ok=True)

            # Check if the file already exists
            if exists(filepath):
                logging.info(f"File already exists: {filepath}. Skipping download.")
                return

            # Download the video with a progress bar
            size_in_bytes = int(response.headers.get('content-length', 0))
            block_size = 1024
            progress_bar = tqdm(total=size_in_bytes, unit='iB', unit_scale=True, desc=f"Downloading {video_filename}")
            with open(filepath, "wb") as file:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    file.write(data)
            progress_bar.close()
            logging.info(f"Downloaded video to {filepath}")
        except Exception as e:
            logging.info(f"Download URL is invalid for {self.name}. Attempting alternate download method.")
            self.download_alternate_work()
# TODO: refactor this class to have a Page base class and subclasses for different types of page
class Page:
    def save_html(self, url, content, artist_name=None, work_name=None):
        """
        Save the HTML content of a page to a local file, replicating the folder structure.
        """
        # Base directory for saving files
        base_dir = DOWNLOAD_PATH

        # If artist_name is provided, create a subdirectory for the artist
        if artist_name:
            base_dir = os.path.join(base_dir, artist_name)

        # If work_name is provided, save as <artist>/<work>/index.html
        if work_name:
            base_dir = os.path.join(base_dir, work_name)
            filename = "index.html"
        else:
            # Save as <artist>/index.html if no work_name is provided
            filename = "index.html"

        # Construct the full file path
        filepath = os.path.join(base_dir, filename)

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save the content to the file
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        logging.info(f"Saved HTML content to {filepath}")

    def get_tables(self, page):
        soup = BeautifulSoup(page.content, "html.parser")
        tables = soup.find_all("table")
        return tables

    # refactor this and get_links to reuse the response for many functions
    def get_artist_description(self, url, artist_name):
        page = requests.get(url)
        # Save the artist HTML
        self.save_html(url, page.text, artist_name=artist_name)

        tables = self.get_tables(page)
        storycontent = tables[1].find("div", class_="storycontent")
        description = storycontent.find_all("p")
        return description

    def get_links(self, url):
        try:
            page = requests.get(url)
            # Save the HTML content
            self.save_html(url, page.text)

            tables = self.get_tables(page)
            # Stupid error handling for DMCA takedown pages
            links = tables[1].find_all("a", string=lambda text: "Marian Goodman" not in text)
            return links
        except Exception as e:
            if page.url == ERROR_URL:
                logging.error(f"Page {page.url} is not found on server", exc_info=True)
            else:
                logging.error(f"Page {page.url} has no artist or works", exc_info=True)

    def get_artists(self, url):
        # refactor to only do one request, not two
        artists_links = self.get_links(url)
        # description = self.get_artist_description(url)
        artists = []
        for artist in artists_links:
            a = Artist()
            a.name = artist.text.strip() 
            a.url = BASE_FILM_URL + artist["href"]
            # a.description = description
            artists.append(a)
        # this convention removes the left nav bar links.
        artists.pop(0)
        return artists

    def get_artist_works(self, artist):
        # not sure why artist is None when run in batch mode
        logging.debug(f"Artist is: {artist}")
        links = self.get_links(artist.url)
        works = []
        for work in links:
            w = Work(name=work.text.strip(), url=BASE_FILM_URL + work["href"], artist=artist)
            works.append(w)
        # this convention removes the left nav bar links.
        for _ in range(2):
            works.pop(0)
        if len(works) == 0:
            logging.info(f"Artist {artist.name} has no works on {artist.url}")
        return works
