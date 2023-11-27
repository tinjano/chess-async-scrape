## Intro
This is a custom-made asynchronous scraper and crawler that extracts basic game data from a chess website.
_________

## Important Notes
- the website in question has an API, so it is recommended to use that if you are interested in chess data. The purpose of this project was simply to create a well-structured and efficient crawler.
- Related to the previous note, do not use this to create an excessive burden on any website or act otherwise questionably.
- The scraper/crawler use proxies. A user should use their own `proxylist` file. The logic is encapsulated in `proxy_manager.py` and used in two lines in the main `scraper.py` file. One may also remove those lines.

## Dependencies
check `requirements.txt`.

## Quick Guide
The class (see `scrape.py`) `Scraper` will retrieve a singles user's games. Use with
```python
Scraper(username).do_it().write_csv(optional_filename)
```
The class `Crawler` will do the same for many users, and one should choose the maximum number of players to be included (default 5). It is recommended to use it with `with` so it will write partial results in case of exceptions.
```python
with Crawler(*usernames, max_players=5) as crawler:
    crawler.do_it()
```

## Known Bugs
No bugs known so far.