from datetime import datetime
import re
from items import Game
from selectolax.parser import HTMLParser


def parse(response, caller):
    tree = HTMLParser(response.text)

    # test whether the page is empty
    try:
        h = tree.css_first('h3.v5-section-content.v5-border-top.archive-games-subtitle')
        if 'No results found.' in h.text():
            return
    except AttributeError:
        pass

    table = tree.css_first('table.table-component.table-hover.archive-games-table')
    for tr in table.css('tr')[1:]:
        game_url = tr.css_first('a.archive-games-background-link').attributes['href']
        game_url = re.findall('\d+', game_url)[0]  # just the number

        time_control = tr.css_first('span.archive-games-game-time').text(deep=False, strip=True)

        user_td = tr.css('a.user-username-component')
        username_white, username_black =\
            user_td[0].text(deep=False, strip=True), user_td[1].text(deep=False, strip=True)

        rating_td = tr.css('span.user-tagline-rating')
        rating_white, rating_black =\
            int(rating_td[0].text(deep=False).strip('()')), int(rating_td[1].text(deep=False).strip('()'))

        res = tr.css_first('div.archive-games-result-wrapper-score').text(strip=True)
        result_white, result_black =\
            float(res[0]) if res[0] != '½' else 0.5, \
            float(res[1]) if res[1] != '½' else 0.5

        acc = tr.css_first('td.table-text-center.archive-games-analyze-cell')
        acc = acc.css('div')
        try:
            acc_white, acc_black = acc[0].text(deep=False), acc[1].text(deep=False)
            acc_white = float(acc_white)
            acc_black = float(acc_black)
        except IndexError:
            acc_white, acc_black = None, None

        moves_td = tr.css_first('td.table-text-center:not(.archive-games-analyze-cell)')
        nr_moves = int(moves_td.css_first('span').text())

        date_td = tr.css_first('td.table-text-right.archive-games-date-cell')
        date = date_td.text(deep=False).strip()
        date = datetime.strptime(date, '%b %d, %Y').date()

        caller.games_list.append(Game(
            username_white,
            username_black,
            rating_white,
            rating_black,
            result_white,
            result_black,
            acc_white,
            acc_black,
            nr_moves,
            time_control,
            game_url,
            date
        ))
