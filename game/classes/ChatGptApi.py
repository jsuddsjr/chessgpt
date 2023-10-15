import aiohttp
import asyncio
import threading

from classes.EventSource import EventSource

API_BASEURL = "http://localhost:8000"

API_GET_HELLO = API_BASEURL + "/api/hello"
API_POST_CREATE_GAME = API_BASEURL + "/api/chess"
API_POST_SAVE_MOVE = API_BASEURL + "/api/chess/{id}/move/{move}"
API_GET_SUGGEST_MOVE = API_BASEURL + "/api/chat/{id}/suggest"
API_GET_CHAT = API_BASEURL + "/api/chat/{id}?message={message}"


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
    def player(self) -> int:
        return self.data["ply"]


class ChatGptApi(object):
    def __init__(self):
        self.game_data: ApiGameCreated = None

        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever).start()

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
        await self._invoke("get", API_GET_HELLO, "hello", self.on_api_hello)

    def create_game(self) -> str:
        """Create a new game"""
        asyncio.run_coroutine_threadsafe(self._create_game(), self.loop)

    async def _create_game(self):
        await self._invoke(
            "post",
            API_POST_CREATE_GAME,
            "create",
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
            "move",
            lambda data: self.on_api_moved(ApiMove(data)),
        )

    def suggest_move(self):
        """Suggest a move in the game"""
        asyncio.run_coroutine_threadsafe(self._suggest_move(), self.loop)

    async def _suggest_move(self):
        await self._invoke(
            "get",
            API_GET_SUGGEST_MOVE.format(id=self.id),
            "suggest",
            self.on_api_suggest,
        )

    def chat(self, message: str):
        """Send a message in the game"""
        asyncio.run_coroutine_threadsafe(self._chat(message), self.loop)

    async def _chat(self, message: str):
        await self._invoke(
            "get",
            API_GET_CHAT.format(id=self.id, message=message),
            "chat",
            self.on_api_chat,
        )

    async def _invoke(
        self, method: str, url: str, source: str, callback: callable, json=None
    ):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=json) as response:
                    if response.status == 200:
                        if response.content_type == "application/json":
                            data = await response.json()
                            callback(data)
                        else:
                            data = await response.text()
                            callback(data)
                    else:
                        self.on_api_error(
                            ApiError(source=source, status=response.status)
                        )
        except Exception as e:
            self.on_api_error(ApiError(source=source, message=str(e), status=500))

    def test_error(self, message: str, status: int):
        """Test error handling"""
        self.on_api_error(ApiError(source=message, status=status))
