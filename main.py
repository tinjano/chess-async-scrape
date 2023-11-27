from scrape import Scraper, Crawler
from proxy_manager import CyclicProxyManager

def test():
    with Crawler('MagnusCarlsen', 'Hikaru', max_players=2) as crawler:
        crawler.do_it()

    # Scraper('hikaru').do_it().write_csv()

    # proxy=CyclicProxyManager().proxy_generator
    # print('ips')
    # for i in range(10):
    #     proxies = next(proxy)
    #     print(proxies)

    # urls = ['https://example.com'] * 3
    # result = asyncio.run(async_batch(urls))
    # print(result)
    pass


def main():
    pass


if __name__ == '__main__':
    test()
    pass
