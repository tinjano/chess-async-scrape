from proxy_manager import CyclicProxyManager, user_agent

proxies = CyclicProxyManager().proxy_generator
from items import Game
from logging_settings import logger

from queue import Queue
from urllib.parse import urlparse, urljoin
import datetime
import re

import requests
import asyncio
import httpx
import pandas as pd
from bs4 import BeautifulSoup


def parse(response, caller):
    soup = BeautifulSoup(response.text, 'html.parser')

    if 'No results found.' in soup.text:
        return None

    table = soup.find('table', class_='table-component table-hover archive-games-table')
    for tr in table.find_all('tr'):
        # header row
        if not tr.has_attr('v-board-popover'):
            continue

        game_url = tr.find('a', class_='archive-games-background-link').get('href')
        # p = urlparse(game_url)
        # game_url = f'{p.scheme}://{p.netloc}{p.path}'  # entire url
        game_url = re.findall('\d+', game_url)[0]  # just the number

        time_control = tr.find('span', class_='archive-games-game-time').text

        user_td = tr.find_all(lambda tag: tag.name == 'a' and tag.has_attr('class')
                                          and 'user-username-component' in tag.get('class'))
        username_white, username_black = user_td[0].text, user_td[1].text

        rating_td = tr.find_all('span', class_='user-tagline-rating')
        rating_white, rating_black = rating_td[0].text.strip('()'), rating_td[1].text.strip('()')

        res = tr.find('div', class_='archive-games-result-wrapper-score')
        res = res.find_all('div')
        result_white, result_black = res[0].text, res[1].text
        if result_white == '½':
            result_white = '0.5'
        if result_black == '½':
            result_black = '0.5'

        acc = tr.find('td', class_='table-text-center archive-games-analyze-cell')
        acc = acc.find_all('div')
        try:
            acc_white, acc_black = acc[0].text, acc[1].text
            acc_white = float(acc_white)
            acc_black = float(acc_black)
        except IndexError:
            acc_white, acc_black = None, None

        moves_td = tr.find(lambda tag: tag.name == 'td' and tag.has_attr('class')
                                       and tag.get('class') == ['table-text-center'])
        nr_moves = moves_td.find('span').text

        date_td = tr.find('td', class_='table-text-right archive-games-date-cell')
        date = date_td.text.strip()
        date = datetime.datetime.strptime(date, '%b %d, %Y').date()

        caller.games_list.append(Game(
            username_white.strip('\n\t '),
            username_black.strip('\n\t '),
            int(rating_white),
            int(rating_black),
            float(result_white),
            float(result_black),
            acc_white,
            acc_black,
            int(nr_moves),
            time_control.strip('\n\t '),
            game_url,
            date
        ))


async def async_request(url, caller, callback):
    async with httpx.AsyncClient(proxies=next(proxies), timeout=10.0) as client:

        try:
            response = await client.get(url, headers=user_agent())
        except Exception as e:
            logger.error(f'Exception {e} found at url {url}'
                         f'The program will continue.')
            return

        try:
            assert response.status_code == 200
        except AssertionError:
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

        # This is not 'truly' necessary
        response = requests.get(self.url, headers=user_agent())
        soup = BeautifulSoup(response.text, 'html.parser')

        for a in soup.find_all('a', class_='v5-tabs-button'):
            if 'Live' in a.text:
                self.url = a.get('href')[:-6]

        title = soup.find('span', class_='v5-title-has-icon')
        game_nr_pattern = r'Games \(([\d\,]+)\)'
        self.nr_games = re.search(game_nr_pattern, title.text).group(1)
        self.nr_games = int(self.nr_games.replace(',', ''))

    def do_it(self):
        pages = min(self.nr_games // 50 + 1, 100)

        page_urls = [f'{self.url}page={number}' for number in range(1, pages + 1)]
        asyncio.run(async_batch(page_urls, self, parse))
        return self

    # only call after do_it
    def write_csv(self, filename=f'output-{datetime.datetime.now()}.csv'):
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
        num_players = 0

        while self.queue.qsize() and num_players < self.max_players:
            player = self.queue.get()
            if player not in self.players_set:
                self.players_set.add(player)
                num_players += 1
            else:
                continue

            try:
                new_list = Scraper(player).do_it().games_list

                for element in new_list:
                    white, black = element.username_white, element.username_black
                    if player == black:
                        self.queue.put(element.username_white)
                    else:
                        self.queue.put(element.username_black)

                self.games_list += new_list

            except Exception as e:
                logger.warning(f'Exception {e} happened when scraping player {player}.'
                               f'The program will continue.')
                continue

        logger.info(f'The program has exhausted the list of players or allowed maximums. Beginning writing to file.')
        self.write_pickle()

    # alias
    crawl = do_it

    def write_pickle(self, filename=f'output-{datetime.datetime.now()}.pkl'):
        df = pd.DataFrame(self.games_list).drop_duplicates(subset='game_url').set_index('game_url')
        df.to_pickle(filename)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f'The crawler ran into '
                         f'{exc_type}:{exc_val}. Writing partial output.')
            self.write_pickle(f'partial-output-{datetime.datetime.now()}.pkl')
