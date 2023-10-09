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

        self._highlighted_squares: List[chess.Square] = []
        self._highlights: arcade.SpriteList[arcade.Sprite] = None

        self.chess_board = chess.Board()

        self.reset()

    def setup(self):
        self.shapes = arcade.ShapeElementList()
        self.labels = arcade.SpriteList()
        self._highlights = arcade.SpriteList()

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

        for square in self._highlighted_squares:
            solid = SpriteSolidColor(SQUARE_SIZE, SQUARE_SIZE, arcade.color.YELLOW)
            solid.position = self.center_of(square)
            solid.alpha = 127
            self._highlights.append(solid)
            self.labels.append(
                self._create_text_sprite(
                    chess.square_name(square),
                    NamedPoint(solid.position[0], solid.position[1]),
                    arcade.color.BLACK,
                )
            )

    def reset(self):
        self._highlighted_squares = [chess.E4, chess.E5, chess.E6]
        self.setup()

        self.pieces = arcade.SpriteList()
        self.chess_board.reset()
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

    @property
    def highlights(self) -> list[chess.Square]:
        return [x for x in self._highlighted_squares]

    @highlights.setter
    def set_highlights(self, value: list[chess.Square]) -> None:
        self._highlighted_squares = value
        self.setup()

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
