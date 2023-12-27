from dataclasses import dataclass
from datetime import datetime

@dataclass
class Game:
    username_white: str
    username_black: str
    rating_white: int
    rating_black: int
    score_white: float
    score_black: float
    acc_white: float
    acc_black: float
    nr_moves: int
    time_control: str
    game_url: str
    date: datetime.date

    def __eq__(self, other):
        return self.game_url == other.game_url

    def __hash__(self):
        return hash(self.game_url)
