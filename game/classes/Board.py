import arcade
import chess

from typing import List
from arcade import Point, NamedPoint, Color, SpriteSolidColor

from classes.Piece import Piece


SQUARE_SIZE = 100
SQUARE_CENTER = SQUARE_SIZE / 2

BOARD_MARGIN = 30
BOARD_CENTER = BOARD_MARGIN + SQUARE_SIZE * 4
BOARD_WIDTH = BOARD_CENTER * 2

ORIGIN_BL = NamedPoint(BOARD_MARGIN, BOARD_MARGIN)


class Board(arcade.Shape):
    COLORS = [arcade.color.WHITE, arcade.color.EMERALD]
    TEXT_COLOR: Color = arcade.color.WHITE

    def __init__(self):
        self.chess_board = chess.Board()
        self.shapes: arcade.ShapeElementList = None
        self.labels: arcade.SpriteList[arcade.Sprite] = None
        self.pieces: arcade.SpriteList[Piece] = None
        self._highlights: arcade.SpriteList[arcade.Sprite] = None
        self._warnings: arcade.SpriteList[arcade.Sprite] = None

        self.origin = ORIGIN_BL
        self.perspective = chess.WHITE

        self.setup()

    def setup(self):
        self.create_board()
        self.reset()

    def create_board(self):
        self.shapes = arcade.ShapeElementList()
        self.labels = arcade.SpriteList()

        self.shapes.center_x = BOARD_CENTER
        self.shapes.center_y = BOARD_CENTER

        self.shapes.append(
            arcade.create_rectangle_filled(
                0,
                0,
                BOARD_WIDTH,
                BOARD_WIDTH,
                arcade.color.BLACK_BEAN,
            )
        )

        centers = [x * SQUARE_SIZE + SQUARE_CENTER for x in range(-4, 4)]
        color_index = 0

        for file in centers:
            color_index += 1
            for rank in centers:
                self.shapes.append(
                    self._create_square(
                        NamedPoint(rank, file), Board.COLORS[color_index % 2]
                    )
                )
                color_index += 1

    def create_labels(self):
        self.labels = arcade.SpriteList()
        margin = BOARD_MARGIN / 2

        for x in range(0, 8):
            center = x * SQUARE_SIZE + SQUARE_CENTER
            if self.perspective == chess.BLACK:
                x = 7 - x

            self.labels.append(
                self._create_text_sprite(
                    str(x + 1),
                    NamedPoint(self.origin.x - margin, self.origin.y + center),
                )
            )
            self.labels.append(
                self._create_text_sprite(
                    str(chr(x + 65)),
                    NamedPoint(self.origin.x + center, self.origin.y - margin),
                )
            )

    def update_pieces(self):
        self.pieces = arcade.SpriteList()
        for square, piece in self.chess_board.piece_map().items():
            self.pieces.append(
                Piece(
                    piece,
                    square,
                    self.center_of(square),
                )
            )

    def update_highlights(self, highlighted_squares: list[chess.Square] = []):
        self._highlights = arcade.SpriteList()
        self._highlights.extra = highlighted_squares

        for square in highlighted_squares:
            solid = SpriteSolidColor(SQUARE_SIZE, SQUARE_SIZE, arcade.color.YELLOW)
            solid.position = self.center_of(square)
            solid.alpha = 127
            self._highlights.append(solid)
            self._highlights.append(
                self._create_text_sprite(
                    chess.square_name(square),
                    NamedPoint(solid.position[0], solid.position[1]),
                    arcade.color.BLACK,
                )
            )

    def update_warnings(
        self, warning_squares: list[chess.Square] = [], warning_type: str = "check"
    ):
        self._warnings = arcade.SpriteList()
        self._warnings.extra = warning_squares

        for square in warning_squares:
            solid = arcade.SpriteCircle(SQUARE_SIZE // 2, arcade.color.RED, True)
            solid.position = self.center_of(square)
            self._warnings.append(solid)
            self._warnings.append(
                self._create_text_sprite(
                    warning_type,
                    NamedPoint(solid.position[0], solid.position[1]),
                    arcade.color.BLACK,
                )
            )

    def reset(self):
        self.chess_board.reset()
        self.update_highlights()
        self.update_pieces()
        self.update_warnings()

    def draw(self):
        self.shapes.draw()
        self.labels.draw()
        self._highlights.draw()
        self.pieces.draw()
        self._warnings.draw()

    def center(self, x, y):
        self.shapes.center_x = x
        self.shapes.center_y = y
        self.origin = NamedPoint(x - SQUARE_SIZE * 4, y - SQUARE_SIZE * 4)
        self.update_pieces()
        self.create_labels()

    def center_of(self, square: chess.Square) -> Point:
        rank = chess.square_rank(square)
        file = chess.square_file(square)

        if self.perspective == chess.BLACK:
            rank = 7 - rank
            file = 7 - file

        return (
            self.origin.x + SQUARE_SIZE * file + SQUARE_CENTER,
            self.origin.y + SQUARE_SIZE * rank + SQUARE_CENTER,
        )

    def square_at(self, x: int, y: int) -> chess.Square:
        file = int((x - self.origin.x) / SQUARE_SIZE)
        rank = int((y - self.origin.y) / SQUARE_SIZE)

        if file < 0 or rank < 0 or file > 7 or rank > 7:
            return None

        if self.perspective is chess.BLACK:
            file = 7 - file
            rank = 7 - rank

        return chess.square(file, rank)

    def move_piece(self, piece: Piece, square: chess.Square) -> bool:
        if not self.is_valid_move(piece, square):
            # Return to original position.
            piece.position = self.center_of(piece.square)
            return False

        self.chess_board.push(chess.Move(piece.square, square))
        self.set_perspective(self.chess_board.turn)

        # Look for warnings
        if self.chess_board.is_check():
            self.update_warnings(self.chess_board.checkers(), "check")
        else:
            self.update_warnings()

        return True

    def is_valid_move(self, piece: Piece, square: chess.Square) -> bool:
        return self.chess_board.is_legal(chess.Move(piece.square, square))

    def legal_moves(self, piece: Piece) -> List[chess.Square]:
        return [
            move.to_square
            for move in self.chess_board.legal_moves
            if move.from_square == piece.square
        ]

    def set_perspective(self, player=chess.WHITE) -> None:
        if player == self.perspective:
            return

        self.perspective = player
        self.update_pieces()
        self.create_labels()
        self.update_highlights()
        self.update_warnings()

    def undo_move(self) -> None:
        if (len(self.chess_board.move_stack)) == 0:
            return

        self.chess_board.pop()
        self.set_perspective(self.chess_board.turn)

    def show_attackers_of(self, x: int, y: int) -> None:
        square = self.square_at(x, y)
        if square in self._warnings.extra:
            return

        attackers = self.chess_board.attackers(not self.chess_board.turn, square)
        self.update_warnings(attackers, "threat")

    def highlight_square_at(self, x: int, y: int) -> None:
        square = self.square_at(x, y)

        # Remove highlight, if no square is selected.
        if square is None:
            if len(self._highlights) > 0:
                self.update_highlights()
            return

        # Skip update, if square is already highlighted.
        if square in self.get_highlights():
            return

        self.update_highlights([square])

    def get_highlights(self) -> List[chess.Square]:
        return self._highlights.extra

    def set_highlights(self, value: List[chess.Square]) -> None:
        self.update_highlights(value)

    highlights = property(get_highlights, set_highlights)

    def _create_square(self, center: NamedPoint, color: Color):
        return arcade.create_rectangle_filled(
            center.x, center.y, SQUARE_SIZE, SQUARE_SIZE, color
        )

    def _create_text_sprite(
        self,
        text: str,
        center: NamedPoint,
        font_color: Color = TEXT_COLOR,
        font_size: int = 15,
    ):
        return arcade.create_text_sprite(
            text,
            center.x,
            center.y,
            font_color,
            font_size,
            anchor_x="center",
            anchor_y="center",
        )
