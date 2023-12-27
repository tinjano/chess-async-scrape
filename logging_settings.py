import logging
import sys

logger = logging.getLogger('chesscom-scrape')

stdout_handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
)

# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')
stdout_handler.setFormatter(formatter)

logger.addHandler(stdout_handler)

# level
logger.setLevel(logging.DEBUG)