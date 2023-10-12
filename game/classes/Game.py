import arcade
import chess
import chess.pgn
import json
import requests

GAME_BASEURL = "http://localhost:8000/api/chess"

class Game(object):
    def __init__(self):
        self.__data = None
        self.board: chess.Board = None

    def create_game(self) -> str:
        '''Create a new game'''
        try:
            response = requests.post(GAME_BASEURL, json={"event":"ChessGPT"})
            if response.status_code is 200:
                self.__data = json.loads(response.content)
                return None
        except Exception:
            return "Failed to load game from server. Is it running?"
    
    @property
    def fen(self):
        return self.__data["fen"]
    
    @property
    def id(self):
        return self.__data["id"]
    
        
    

    

        