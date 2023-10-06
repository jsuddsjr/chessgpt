from .models import Game, Move, ChatHistory

from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import ModelSchema, Schema, NinjaAPI
from typing import List

import chess
import chess.pgn
import json
import openai
import requests

api = NinjaAPI(title="ChessGPT API", description="API for ChessGPT.", version="0.1.0")

empty_date = "????.??.??"


class GameRequestModel(Schema):
    owner_id: int = None
    white: str = "White"
    black: str = "Black"
    event: str = "Casual Game"
    date: str = empty_date
    round: int = 1
    outcome: str = "*"
    fen: str = chess.STARTING_FEN


class GameModelSchema(ModelSchema):
    class Config:
        model = Game
        model_fields = "__all__"


class MoveModelSchema(ModelSchema):
    class Config:
        model = Move
        model_fields = "__all__"


class ChatHistoryModelSchema(ModelSchema):
    role: str = "user"
    fname: str = None
    content: str = "Black to d5."

    class Config:
        model = ChatHistory
        model_fields = ["role", "fname", "content"]


class ErrorSchema(Schema):
    error: str = "Error"


@api.get("/hello")
async def hello_world(request):
    completion = openai.Completion.acreate(
        model="gpt-3.5-turbo-0613",
        messages=[{"role": "user", "content": "Warm greetings to you!"}],
    )
    return completion.choices[0].text


@api.get(
    "/chess",
    response={200: List[GameModelSchema]},
    summary="Get a list of chess games.",
)
def get_chess_games(request):
    games = Game.objects.all()
    return games


@api.post(
    "/chess",
    response={200: GameModelSchema, 400: ErrorSchema},
    summary="Create a new chess game.",
)
async def post_chess_game(request, payload: GameRequestModel, event: str = None):
    # From query params.
    if event:
        payload.event = event

    if payload.owner_id:
        payload.owner = get_object_or_404(User, id=payload.owner_id)
    else:
        payload.owner_id = None

    try:
        if (
            (payload.date == empty_date)
            or (payload.date == "")
            or (payload.date == None)
        ):
            payload.date = timezone.now().strftime("%Y.%m.%d")

        pgn = chess.pgn.Game(
            [
                ("Event", payload.event),
                ("Date", payload.date),
                ("White", payload.white),
                ("Black", payload.black),
                ("Round", payload.round),
                ("Result", payload.outcome),
            ]
        )

        if payload.fen:
            pgn.setup(payload.fen)

        exporter = chess.pgn.StringExporter(headers=True)

        game = await Game.objects.acreate(pgn=pgn.accept(exporter), **payload.dict())

        await ChatHistory.objects.acreate(
            game=game, role="system", content="You are a chess master."
        )
        await ChatHistory.objects.acreate(
            game=game,
            role="user",
            content="Respond in Standard Algebraic Notation (SAN) using 'suggest_next_move' function.",
        )
        await ChatHistory.objects.acreate(
            game=game, role="assistant", content="{'san': 'e4'}"
        )
        await ChatHistory.objects.acreate(
            game=game,
            role="user",
            content="Let's start a new game. You are playing white. It's your turn.",
        )

        return game

    except Exception as e:
        return 400, {"error": str(e)}


@api.get("/chess/{game_id}", response=GameModelSchema)
def get_chess_game(request, game_id):
    """Get a chess game by ID."""
    game = get_object_or_404(Game, id=game_id)
    return game


@api.post("/chess/{game_id}/next/{move}")
def post_chess_next_move(request, game_id, move) -> HttpResponseRedirect:
    game = get_object_or_404(Game, id=game_id)
    ChatHistory.objects.create(game=game, role="user", content=move)
    url = request.build_absolute_uri(f"/api/chess/{game_id}/next")
    return requests.post(url).json()


@api.get("/chess/{game_id}/moves", response=List[MoveModelSchema])
def get_chess_game_moves(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    moves = Move.objects.filter(game=game)
    return moves


@api.post("/chess/{game_id}/moves", response=MoveModelSchema)
def post_chess_game_move(request, game_id, payload: MoveModelSchema):
    game = get_object_or_404(Game, id=game_id)

    last_move = Move.objects.filter(game=game).last()
    if last_move:
        payload.color = 1 if last_move.color == 2 else 2
    else:
        payload.color = 1

    payload.game = game
    move = Move.objects.create(**payload.dict())
    return move


@api.get("/chat/{game_id}", response=List[ChatHistoryModelSchema])
def get_chat_history(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return ChatHistory.objects.filter(game=game)


@api.post("/chat/{game_id}", response=ChatHistoryModelSchema)
def post_chat_history(request, game_id, payload: ChatHistoryModelSchema):
    game = get_object_or_404(Game, id=game_id)
    return ChatHistory.objects.create(game=game, **payload.dict())


@api.get("/chat/{game_id}/suggest")
def post_chess_next(request, game_id):
    """Suggest the next move in a chess game."""
    game = get_object_or_404(Game, id=game_id)
    messages = ChatHistory.objects.filter(game=game)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[x.toMessage() for x in messages],
        temperature=1.1,
        functions=[
            {
                "name": "suggest_next_chess_move",
                "description": "Suggest the next move in a chess game, such as 'e4' or 'Nf3'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "move": {
                            "type": "string",
                            "description": "Standard Algebraic Notation (SAN) for the next move.",
                        },
                    },
                    "required": ["move"],
                },
            }
        ],
        function_call={"name": "suggest_next_chess_move"},
    )

    message = completion.choices[0].message

    if hasattr(message, "function_call"):
        fn = message.function_call
        ChatHistory.objects.create(
            game=game, role="assistant", fname=fn.name, content=fn.arguments
        )
        return json.loads(fn.arguments)
    else:
        ChatHistory.objects.create(game=game, role="assistant", content=message.content)
        return message.content
