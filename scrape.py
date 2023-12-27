from proxy_manager import CyclicProxyManager, user_agent

proxies = CyclicProxyManager().proxy_generator
from items import Game
from parse import parse
from logging_settings import logger

import os.path
import traceback
from queue import Queue
from urllib.parse import urlparse, urljoin
from datetime import datetime
import re

import requests
import asyncio
import httpx
import pandas as pd
from selectolax.parser import HTMLParser


async def async_request(url, caller, callback):
    async with httpx.AsyncClient(proxies=next(proxies), timeout=10.0) as client:

        try:
            response = await client.get(url, headers=user_agent())
        except Exception as e:
            logger.error(f'Exception {e} found at url {url}'
                         f'The program will continue.')
            return

        if response.status_code != 200:
            # raise Exception(f'Request to {url} returned status code {response.status_code}.')
            logger.error(f'Status code {response.status_code} from {url}. The program will continue')
            return

        logger.debug(f'Response from {url}: {response.status_code}')
        callback(response, caller)


async def async_batch(urls, caller, callback):
    await asyncio.gather(*[async_request(url, caller, callback) for url in urls])


class Scraper:
    base_url = 'https://www.chess.com/'

    def __init__(self, username):
        path = f'games/archive/{username}'
        self.url = urljoin(self.base_url, path)
        self.games_list = []

        response = requests.get(self.url, headers=user_agent())
        tree = HTMLParser(response.text)

        for a in tree.css('a.v5-tabs-button'):
            if 'Live' in a.text(deep=False):
                self.url = a.attributes['href'][:-6]

        title = tree.css_first('span.v5-title-has-icon')
        game_nr_pattern = r'Games \(([\d\,]+)\)'
        self.nr_games = re.search(game_nr_pattern, title.text(deep=False)).group(1)
        self.nr_games = int(self.nr_games.replace(',', ''))

    def do_it(self):
        pages = min(self.nr_games // 50 + 1, 100)

        page_urls = [f'{self.url}page={number}' for number in range(1, pages + 1)]
        asyncio.run(async_batch(page_urls, self, parse))
        return self

    # only call after do_it
    def write_csv(self, filename=f'output-{datetime.now()}.csv'):
        df = pd.DataFrame(self.games_list).set_index('game_url')
        df.to_csv(filename, index=True)


class Crawler:
    def __init__(self, *args, max_players=5):
        self.queue = Queue()
        for arg in args:
            self.queue.put(arg)

        self.players_set = set()
        self.games_list = []
        self.max_players = max_players

    def do_it(self):
        filename = f'output-{datetime.now()}.parquet'
        num_players = 0

        while not self.queue.empty() and num_players <= self.max_players:
            player = self.queue.get()

            temp_size = len(self.players_set)
            self.players_set.add(player)
            if len(self.players_set) == temp_size:
                continue
            else:
                num_players += 1

            try:
                new_list = Scraper(player).do_it().games_list

                for element in new_list:
                    white, black = element.username_white, element.username_black
                    if player == black:
                        self.queue.put(element.username_white)
                    else:
                        self.queue.put(element.username_black)

                self.games_list.extend(new_list)
                # logger.info(f'Game list length now at {len(self.games_list)}')

                if len(self.games_list) > 100_000:
                    self.write_parquet(filename)
                    self.games_list = []

            except Exception as e:
                logger.error(f'Exception {e} happened when scraping player {player}.'
                             f'The program will continue.')
                continue

        logger.info(f'The program has exhausted the list of players or allowed maximums. Beginning writing to file.')
        self.write_parquet(filename)

    # alias
    crawl = do_it

    def write_parquet(self, filename=f'output-{datetime.now()}.parquet'):
        df = pd.DataFrame(self.games_list).drop_duplicates(subset='game_url').set_index('game_url')
        df.date = pd.to_datetime(df.date, errors='coerce')
        df.to_parquet(filename, engine='fastparquet', append=os.path.exists(filename))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            traceback_lines = traceback.format_tb(exc_tb)
            logger.error('An exception occurred...', exc_info=True)

            if all(['write_parquet' not in line for line in traceback_lines]):
                logger.info('Writing partial output...')
                self.write_parquet(f'partial-output-{datetime.now()}.parquet')
            else:
                logger.info('Could not save data.')
