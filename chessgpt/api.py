from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from ninja import ModelSchema, Schema, NinjaAPI
from typing import List
from .models import Game, Move, ChatHistory
import openai
import requests
import json

api = NinjaAPI(title="ChessGPT API", description="API for ChessGPT.", version="0.1.0")


class GameRequestModel(Schema):
    owner_id: int = None
    name: str = "Untitled Game"


class GameModelSchema(ModelSchema):
    class Config:
        model = Game
        model_fields = "__all__"


class MoveModelSchema(ModelSchema):
    class Config:
        model = Move
        model_fields = "__all__"


@api.get("/hello")
async def hello_world(request):
    completion = openai.Completion.acreate(
        model="gpt-3.5-turbo-0613",
        messages=[{"role": "user", "content": "Warm greetings to you!"}],
    )
    return completion.choices[0].text


@api.get("/chess", response=List[GameModelSchema])
async def get_chess_games(request):
    games = await Game.objects.aget()
    return games


@api.get("/chess/{game_id}", response=GameModelSchema)
def get_chess_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return game


@api.post("/chess/{game_id}/next")
def post_chess_next(request, game_id) -> dict:
    game = get_object_or_404(Game, id=game_id)
    messages = ChatHistory.objects.filter(game=game)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[x.toMessage() for x in messages],
        functions=[
            {
                "name": "get_chess_move",
                "description": "Gets next move in algebraic notation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "move": {
                            "type": "string",
                            "description": "The move, e.g. 'e4' or 'Nf3'",
                        },
                    },
                    "required": ["move"],
                },
            }
        ],
        function_call="auto",
    )
    move = completion.choices[0].message.function_call.arguments
    ChatHistory.objects.create(
        game=game, role="function", fname="get_chess_move", content=move
    )
    return json.loads(move)


@api.post("/chess/{game_id}/next/{move}")
def post_chess_next_move(request, game_id, move) -> HttpResponseRedirect:
    game = get_object_or_404(Game, id=game_id)
    ChatHistory.objects.create(game=game, role="user", content=move)
    url = request.build_absolute_uri(f"/api/chess/{game_id}/next")
    return requests.post(url).json()


@api.post("/chess", response=GameModelSchema)
async def post_chess_game(request, payload: GameRequestModel):
    game = await Game.objects.acreate(**payload.dict())

    await ChatHistory.objects.acreate(
        game=game, role="system", content="You are a chess player."
    )
    await ChatHistory.objects.acreate(
        game=game, role="user", content="You are white. What's your first move?"
    )
    await ChatHistory.objects.acreate(
        game=game,
        role="user",
        content="Return a single move in algebraic notation.",
    )

    return game


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
