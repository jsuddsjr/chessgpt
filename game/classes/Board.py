import arcade
import chess

from typing import List
from arcade import Point, NamedPoint, Color, SpriteSolidColor

from classes.Piece import Piece


SQUARE_SIZE = 100
SQUARE_CENTER = SQUARE_SIZE / 2

BOARD_MARGIN = 50
BOARD_CENTER = BOARD_MARGIN + SQUARE_SIZE * 4


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
        self.setup()

    def setup(self):
        self.create_board()
        self.reset()

    def create_board(self):
        self.shapes = arcade.ShapeElementList()
        self.labels = arcade.SpriteList()

        centers = [x * SQUARE_SIZE + SQUARE_CENTER + BOARD_MARGIN for x in range(0, 8)]
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

        for x, center in enumerate(centers):
            self.labels.append(
                self._create_text_sprite(
                    str(x + 1), NamedPoint(BOARD_MARGIN / 2, center)
                )
            )
            self.labels.append(
                self._create_text_sprite(
                    str(chr(x + 65)),
                    NamedPoint(center, BOARD_MARGIN / 2),
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
        self.shapes.move(x - BOARD_CENTER, y - BOARD_CENTER)
        self.labels.move(x - BOARD_CENTER, y - BOARD_CENTER)
        self.pieces.move(x - BOARD_CENTER, y - BOARD_CENTER)
        self._highlights.move(x - BOARD_CENTER, y - BOARD_CENTER)

    def center_of(self, square: chess.Square) -> Point:
        return (
            self.shapes.center_x + SQUARE_SIZE * (chess.square_file(square) + 1),
            self.shapes.center_y + SQUARE_SIZE * (chess.square_rank(square) + 1),
        )

    def move_piece(self, piece: Piece, square: chess.Square) -> bool:
        if not self.is_valid_move(piece, square):
            # Return to original position.
            piece.position = self.center_of(piece.square)
            return False

        self.chess_board.push(chess.Move(piece.square, square))
        self.update_pieces()

        # Look for warnings
        if self.chess_board.is_check():
            self.update_warnings(self.chess_board.checkers(), "check")
        else:
            self.update_warnings()

        return True

    def piece_at(self, x: int, y: int) -> Piece:
        square = self.square_at(x, y)
        if square is None:
            return None

        for piece in self.pieces:
            if piece.square == square:
                return piece

    def square_at(self, x: int, y: int) -> chess.Square:
        file = int((x - BOARD_MARGIN - self.shapes.center_x) / SQUARE_SIZE)
        rank = int((y - BOARD_MARGIN - self.shapes.center_y) / SQUARE_SIZE)

        if file < 0 or rank < 0 or file > 7 or rank > 7:
            return None

        return chess.square(file, rank)

    def is_valid_move(self, piece: Piece, square: chess.Square) -> bool:
        return self.chess_board.is_legal(chess.Move(piece.square, square))

    def legal_moves(self, piece: Piece) -> List[chess.Square]:
        return [
            move.to_square
            for move in self.chess_board.legal_moves
            if move.from_square == piece.square
        ]

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
