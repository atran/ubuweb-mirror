import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = os.getenv("BASE_URL")
FILM_URL = os.getenv("FILM_URL")
BASE_FILM_URL = os.getenv("BASE_FILM_URL")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")
ERROR_URL = os.getenv("ERROR_URL")
BROKEN_PAGES = list(map(int, os.getenv("BROKEN_PAGES").split(',')))

'''
215
https://www.ubu.com/film/clarke_ornette.html
this index uses Javascript to render the link to media. the
streaming video uses a service called https://criticalcommons.org/embed?m=fwqF8eomo
which is not valid in youtube-dl
15 page not found, redirect
9 dmca takedown, zero works.
'''