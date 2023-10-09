import arcade
from typing import List
from arcade import Point, NamedPoint, Color, SpriteSolidColor
from classes.Piece import Piece, chess


SQUARE_SIZE = 100
SQUARE_CENTER = SQUARE_SIZE / 2

BOARD_MARGIN = 50
BOARD_CENTER = BOARD_MARGIN + SQUARE_SIZE * 4


class Board(arcade.Shape):
    COLORS = [arcade.color.WHITE, arcade.color.EMERALD]
    TEXT_COLOR: Color = arcade.color.WHITE

    def __init__(self):
        self.shapes: arcade.ShapeElementList = None
        self.labels: arcade.SpriteList[arcade.Sprite] = None
        self.pieces: arcade.SpriteList[Piece] = None

        self._highlighted_squares: List[chess.Square] = None
        self._highlights: arcade.SpriteList[arcade.Sprite] = None

        self.chess_board = chess.Board()

        self.reset()

    def setup(self):
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

    def update_highlights(self):
        self._highlights = arcade.SpriteList()
        if self._highlighted_squares is None:
            return

        for square in self._highlighted_squares:
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

    def reset(self):
        self._highlighted_squares = None
        self.chess_board.reset()
        self.update_highlights()
        self.setup()

        self.pieces = arcade.SpriteList()
        for square, piece in self.chess_board.piece_map().items():
            self.pieces.append(
                Piece(
                    piece,
                    square,
                    self.center_of(square),
                )
            )

    def draw(self):
        self.shapes.draw()
        self._highlights.draw()
        self.labels.draw()
        self.pieces.draw()

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
        piece.position = self.center_of(square)
        piece.square = square
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

    def highlight_square_at(self, x: int, y: int) -> None:
        square = self.square_at(x, y)
        if square is None:
            if self._highlighted_squares is None:
                return

            self._highlighted_squares = None
            self.update_highlights()
            return

        if (
            self._highlighted_squares is not None
            and square in self._highlighted_squares
        ):
            return

        self._highlighted_squares = [square]
        self.update_highlights()

    def get_highlights(self) -> list[chess.Square]:
        return self._highlighted_squares

    def set_highlights(self, value: list[chess.Square]) -> None:
        self._highlighted_squares = value
        self.update_highlights()

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
