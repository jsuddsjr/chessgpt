import aiohttp
import asyncio
import threading

from classes.EventSource import EventSource

API_BASEURL = "http://localhost:8000"

API_GET_HELLO = "/api/hello"
API_POST_CREATE_GAME = "/api/chess"
API_POST_SAVE_MOVE = "/api/chess/{id}/move/{move}"
API_GET_SUGGEST_MOVE = "/api/chat/{id}/suggest"
API_GET_CHAT = "/api/chat/{id}?message={message}"


class ApiError:
    def __init__(self, message: str = "", source: str = "", status: int = 0):
        self.message = message
        self.source = source
        self.status = status


class ApiGameCreated:
    def __init__(self, data: dict):
        self.data = data

    @property
    def id(self) -> int:
        return self.data["id"]

    @property
    def fen(self) -> str:
        return self.data["fen"]


class ApiMove:
    def __init__(self, data: dict):
        self.data = data

    @property
    def id(self) -> int:
        return self.data["id"]

    @property
    def fen(self) -> str:
        return self.data["fen"]

    @property
    def uci(self) -> str:
        return self.data["uci"]

    @property
    def ply(self) -> int:
        return self.data["ply"]

    @property
    def san(self) -> str:
        return self.data["san"]

    @property
    def turn(self) -> int:
        return (self.data["ply"] + 1) % 2

    @property
    def outcome(self) -> str:
        return self.data["outcome"]


class ChatGptApi(object):
    def __init__(self):
        self.game_data: ApiGameCreated = None

        self.loop = asyncio.new_event_loop()

        ## Start a new thread that will exit when the main thread ends (daemon=True)
        threading.Thread(
            target=self.loop.run_forever, daemon=True, name="ChatGptApi"
        ).start()

        self.on_api_hello = EventSource("on_api_hello")
        self.on_api_error = EventSource("on_api_error")
        self.on_api_moved = EventSource("on_api_moved")
        self.on_api_suggest = EventSource("on_api_suggest")
        self.on_api_chat = EventSource("on_api_chat")
        self.on_api_created = EventSource("on_api_created")

    @property
    def id(self) -> int:
        return self.game_data.id if self.game_data else 0

    def hello(self):
        """Greetings from the API"""
        asyncio.run_coroutine_threadsafe(self._hello(), self.loop)

    async def _hello(self):
        await self._invoke("get", API_GET_HELLO, self.on_api_hello)

    def create_game(self) -> str:
        """Create a new game"""
        asyncio.run_coroutine_threadsafe(self._create_game(), self.loop)

    async def _create_game(self):
        await self._invoke(
            "post",
            API_POST_CREATE_GAME,
            self._save_game,
            json={"event": "ChessGPT"},
        )

    def _save_game(self, data):
        self.game_data = ApiGameCreated(data)
        self.on_api_created(self.game_data)

    def make_move(self, move: str):
        """Make a move in the game"""
        asyncio.run_coroutine_threadsafe(self._make_move(move), self.loop)

    async def _make_move(self, move: str):
        await self._invoke(
            "post",
            API_POST_SAVE_MOVE.format(id=self.id, move=move),
            lambda data: self.on_api_moved(ApiMove(data)),
        )

    def suggest_move(self):
        """Suggest a move in the game"""
        asyncio.run_coroutine_threadsafe(self._suggest_move(), self.loop)

    async def _suggest_move(self):
        await self._invoke(
            "get",
            API_GET_SUGGEST_MOVE.format(id=self.id),
            self.on_api_suggest,
        )

    def chat(self, message: str):
        """Send a message in the game"""
        asyncio.run_coroutine_threadsafe(self._chat(message), self.loop)

    async def _chat(self, message: str):
        await self._invoke(
            "get",
            API_GET_CHAT.format(id=self.id, message=message),
            self.on_api_chat,
        )

    async def _invoke(self, method: str, url: str, callback: callable, json=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, API_BASEURL + url, json=json
                ) as response:
                    if response.status == 200:
                        if response.content_type == "application/json":
                            data = await response.json()
                            callback(data)
                        else:
                            data = await response.text()
                            callback(data)
                    elif response.status == 400:
                        error = await response.json()
                        self.on_api_error(
                            ApiError(
                                source=url,
                                status=response.status,
                                message=error["error"],
                            )
                        )
                    else:
                        self.on_api_error(
                            ApiError(
                                source=url,
                                status=response.status,
                                message=response.reason,
                            )
                        )
        except Exception as e:
            self.on_api_error(ApiError(source=url, message=str(e), status=0))
