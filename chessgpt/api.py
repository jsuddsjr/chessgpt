from .models import Game, Move, ChatHistory
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import ModelSchema, Schema, NinjaAPI
from typing import List

import chess
import chess.pgn
import io
import openai
import requests

api = NinjaAPI(title="ChessGPT API", description="API for ChessGPT.", version="0.1.0")

empty_date = "????.??.??"
exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)


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
    content: str = "Black to d5."

    class Config:
        model = ChatHistory
        model_fields = ["role", "content"]


class ErrorSchema(Schema):
    error: str = "Error"


@api.get("/hello", tags=["hello"], response={200: str}, summary="Hello world!")
async def hello_world(request):
    completion = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo-0613",
        temperature=0.8,
        messages=[
            {
                "role": "system",
                "content": "You are a friendly chess player.",
            },
            {"role": "user", "content": "Hello!"},
        ],
    )

    content = completion.choices[0].message.content
    return content


@api.get(
    "/chess",
    tags=["games"],
    response={200: List[GameModelSchema]},
    summary="Get a list of chess games.",
)
def get_chess_games(request):
    games = Game.objects.all()
    return games


@api.post(
    "/chess",
    tags=["games"],
    response={200: GameModelSchema, 400: ErrorSchema},
    summary="Create a new chess game.",
)
async def post_chess_game(request, payload: GameRequestModel, event: str = None):
    # From query params.
    if event:
        payload.event = event

    if payload.owner_id:
        payload.owner = await sync_to_async(get_object_or_404)(
            User, id=payload.owner_id
        )
    else:
        payload.owner_id = None

    try:
        if (
            (payload.date == empty_date)
            or (payload.date == "")
            or (payload.date is None)
        ):
            payload.date = timezone.now().strftime("%Y.%m.%d")

        game = await Game.objects.acreate(pgn="*", **payload.dict())

        await ChatHistory.objects.acreate(
            game=game,
            role="system",
            content="Generate chess moves in UCI format, e.g. 'e2e4' or 'e7e8q'. No other text is allowed.",
        )
        await ChatHistory.objects.acreate(
            game=game, role="user", content="White, what's your opening move?"
        )

        return game

    except Exception as e:
        return 400, {"error": str(e)}


@api.get(
    "/chess/{game_id}",
    tags=["games"],
    response=GameModelSchema,
    summary="Get a chess game by ID.",
)
def get_chess_game(request, game_id):
    """Get a chess game by ID."""
    game = get_object_or_404(Game, id=game_id)
    return game


@api.get(
    "/chess/{game_id}/pgn",
    tags=["pgn"],
    summary="Get a PGN file for this game.",
)
async def get_chess_game_pgn(request, game_id: int) -> HttpResponse:
    """Get a chess game by ID."""
    game = await sync_to_async(get_object_or_404)(Game, id=game_id)

    chessGame = chess.pgn.read_game(io.StringIO(game.pgn))
    chessGame.headers = chess.pgn.Headers(
        [
            ("Event", game.event),
            ("Date", game.date.strftime("%Y.%m.%d")),
            ("White", game.white),
            ("Black", game.black),
            ("Round", game.round),
            ("Result", game.outcome),
        ]
    )
    return HttpResponse(str(chessGame), content_type="text/plain")


@api.post(
    "/chess/{game_id}/move/{move}",
    tags=["moves"],
    response={200: MoveModelSchema, 400: ErrorSchema},
    summary="Make a move in a chess game.",
)
async def post_chess_next_move(request, game_id: int, move: str):
    game = await sync_to_async(get_object_or_404)(Game, id=game_id)
    # url = request.build_absolute_uri(f"/api/chess/{game_id}/next")
    # return requests.post(url).json()
    chessBoard = chess.Board(game.fen)
    chessMove = None

    try:
        chessMove = chess.Move.from_uci(move)
    except chess.InvalidMoveError:
        try:
            chessMove = chessBoard.push_san(move)
        except Exception as e2:
            return 400, {"error": str(e2)}
    except Exception as e1:
        return 400, {"error": str(e1)}

    if chessMove not in chessBoard.legal_moves:
        return 400, {"error": f"Not a legal move: {move}"}

    moveObj = await Move.objects.acreate(
        game=game,
        uci=chessMove.uci(),
        san=chessBoard.san(chessMove),
        ply=chessBoard.ply(),
        fen=game.fen,
    )

    await ChatHistory.objects.acreate(game=game, role="user", content=chessMove.uci())
    chessBoard.push(chessMove)
    game.fen = chessBoard.fen()

    chessNode = chess.pgn.read_game(io.StringIO(game.pgn)).end()
    chessNode.add_main_variation(chessMove)
    game.pgn = chessNode.game().accept(exporter)
    await game.asave()
    return moveObj


@api.get(
    "/chess/{game_id}/move",
    tags=["moves"],
    response=List[MoveModelSchema],
    summary="Get a list of moves in a chess game.",
)
def get_chess_game_moves(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    moves = Move.objects.filter(game=game)
    return moves


@api.get(
    "/chat/{game_id}/history",
    tags=["history"],
    response=List[ChatHistoryModelSchema],
    summary="Get chat history.",
)
def get_chat_history(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return ChatHistory.objects.filter(game=game)


@api.post(
    "/chat/{game_id}/history",
    tags=["history"],
    response=ChatHistoryModelSchema,
    summary="Append a chat message to history.",
)
def post_chat_history(request, game_id, payload: ChatHistoryModelSchema):
    game = get_object_or_404(Game, id=game_id)
    return ChatHistory.objects.create(game=game, **payload.dict())


@api.get(
    "/chat/{game_id}",
    tags=["chat"],
    summary="Chat in real-time.",
)
def get_chat(request, game_id: int, message: str) -> HttpResponse:
    game = get_object_or_404(Game, id=game_id)
    hist = ChatHistory.objects.filter(game=game)
    msgs = [x.toMessage() for x in hist]

    msgs.append({"role": "system", "content": "You are a lively conversationalist."})
    msgs.append({"role": "user", "content": message})

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613", temperature=0.8, messages=msgs
    )

    reply = completion.choices[0].message.content

    ChatHistory.objects.create(game=game, role="user", content=message)
    ChatHistory.objects.create(game=game, role="assistant", content=reply)
    return HttpResponse(reply, content_type="text/plain")


@api.get("/chat/{game_id}/suggest", tags=["chat"], summary="Suggest the next move.")
def post_chess_next(request, game_id):
    """Suggest the next move in a chess game."""
    game = get_object_or_404(Game, id=game_id)
    hist = ChatHistory.objects.filter(game=game)
    msgs = [x.toMessage() for x in hist]

    ## A few more messages to help GPT-3 understand the context.
    ## msgs.append({"role": "assistant", "content": "FEN: " + game.fen})
    msgs.append({"role": "assistant", "content": "PGN: " + game.pgn})
    msgs.append({"role": "user", "content": "What's the best next move?"})

    legal_moves = [x.uci() for x in chess.Board(game.fen).legal_moves]
    msgs.append({"role": "assistant", "content": "Legal moves: " + str(legal_moves)})

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        temperature=0.6,
        messages=msgs,
    )

    message = completion.choices[0].message
    return message.content
