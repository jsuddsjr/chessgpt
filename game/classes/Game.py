import chess
import chess.pgn
import json
import requests

GAME_BASEURL = "http://localhost:8000/api/chess"


class Game(object):
    def __init__(self):
        self.__data = {"fen": chess.STARTING_FEN, "id": 0}
        self.board: chess.Board = None

    def create_game(self) -> bool:
        """Create a new game"""
        response = requests.post(GAME_BASEURL, json={"event": "ChessGPT"})
        if response.status_code == 200:
            self.__data = json.loads(response.content)
            return True
        return False

    @property
    def fen(self):
        return self.__data["fen"]

    @property
    def id(self):
        return self.__data["id"]
