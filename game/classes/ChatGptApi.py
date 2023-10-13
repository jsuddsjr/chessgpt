import aiohttp
import asyncio
import threading

import chess
import chess.pgn

from classes.EventSource import EventSource

API_BASEURL = "http://localhost:8000"

API_GET_HELLO = API_BASEURL + "/api/hello"
API_POST_CREATE_GAME = API_BASEURL + "/api/chess"
API_POST_SAVE_MOVE = API_BASEURL + "/api/chess/{id}/move/{move}"
API_GET_SUGGEST_MOVE = API_BASEURL + "/api/chat/{id}/suggest"
API_GET_CHAT = API_BASEURL + "/api/chat/{id}?message={message}"


class ChatGptApi(object):
    def __init__(self):
        self.__game_data = {"fen": chess.STARTING_FEN, "id": 0}
        self.loop = asyncio.new_event_loop()

        threading.Thread(target=self.loop.run_forever).start()

        self.on_data_received = EventSource("on_api_update")
        self.on_data_error = EventSource("on_error_message")
        self.on_suggest_move = EventSource("on_suggest_move")
        self.on_hello = EventSource("on_hello")

    def hello(self):
        """Greetings from the API"""
        asyncio.run_coroutine_threadsafe(self.__hello(), self.loop)

    async def __hello(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(API_GET_HELLO) as response:
                if response.status == 200:
                    data = await response.json()
                    self.on_hello(data)
                else:
                    self.on_data_error(event="hello", status=response.status)

    def create_game(self) -> str:
        """Create a new game"""
        asyncio.run_coroutine_threadsafe(self.__create_game(), self.loop)

    async def __create_game(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_POST_CREATE_GAME, json={"event": "ChessGPT"}
            ) as response:
                if response.status == 200:
                    self.__game_data = await response.json()
                    self.on_data_received(event="create_game", data=self.__game_data)
                else:
                    self.on_data_error(event="create_game", status=response.status)

    def make_move(self, move: str):
        """Make a move in the game"""
        asyncio.run_coroutine_threadsafe(self.__make_move(move), self.loop)

    async def __make_move(self, move: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_POST_SAVE_MOVE.format(id=self.id, move=move)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.on_data_received(data)
                else:
                    self.on_data_error(event="make_move", status=response.status)

    def suggest_move(self):
        """Suggest a move in the game"""
        asyncio.run_coroutine_threadsafe(self.__suggest_move(), self.loop)

    async def __suggest_move(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(API_GET_SUGGEST_MOVE.format(id=self.id)) as response:
                if response.status == 200:
                    data = await response.json()
                    self.on_suggest_move(data)
                else:
                    self.on_data_error(event="suggest_move", status=response.status)

    def chat(self, message: str):
        """Send a message in the game"""
        asyncio.run_coroutine_threadsafe(self.__chat(message), self.loop)

    async def __chat(self, message: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_GET_CHAT.format(id=self.id, message=message)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.on_data_received(event="chat", data=data)
                else:
                    self.on_data_error(event="chat", status=response.status)

    @property
    def fen(self):
        return self.__game_data["fen"]

    @property
    def id(self):
        return self.__game_data["id"]
