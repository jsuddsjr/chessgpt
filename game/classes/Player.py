import chess
import requests

class PlayerEvents:
    def __init__(self):
        self.__handlers = []
    
    def __iadd__(self, handler):
        self.__handlers.append(handler)

    def __isub__(self, handler):
        self.__handlers.remove(handler)

    def __call__(self, *args, **kwargs):
        for handler in self.__handlers:
            try:
                handler(*args, **kwargs)
            except:
                pass

class Player(object):
    def __init__(self):
        self.endpointUrl = "http://localhost:3000/api/chess"