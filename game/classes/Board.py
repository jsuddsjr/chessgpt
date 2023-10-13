import arcade
import chess
import logging
import math

from typing import List
from arcade import NamedPoint, Color, SpriteSolidColor

from classes.Piece import Piece
from classes.EventSource import EventSource

LOG = logging.getLogger(__name__)

SQUARE_SIZE = 100
SQUARE_CENTER = SQUARE_SIZE / 2

BOARD_MARGIN = 30
BOARD_HALF = SQUARE_SIZE * 4
BOARD_CENTER = BOARD_MARGIN + BOARD_HALF
BOARD_WIDTH = BOARD_CENTER * 2

CENTER_PT = NamedPoint(BOARD_CENTER, BOARD_CENTER)

COLOR_WHITE = arcade.make_transparent_color(arcade.color.WHITE_SMOKE, 1 << 7)
COLOR_BLACK = arcade.make_transparent_color(arcade.color.DARK_OLIVE_GREEN, 1 << 7)
COLOR_BOARD = arcade.make_transparent_color(arcade.color.BLACK_BEAN, 1 << 5)

TEXT_COLOR: Color = arcade.color.WHITE

ROTATE_SPEED = 135  ## degrees per second
ALPHA_SPEED = 127  ## alpha per second


class Board(arcade.Shape):
    """A chess board visualizer."""

    COLORS = [COLOR_WHITE, COLOR_BLACK]

    def __init__(
        self,
        fen: str = chess.STARTING_FEN,
        center: NamedPoint = CENTER_PT,
        scale: float = 1.0,  # NOT_USED
    ):
        """Creates a new board with the given FEN string."""

        self.texture = None
        self.scale = 1.0

        self.chess_board = chess.Board(fen)
        self.squares: arcade.ShapeElementList = None
        self.labels: arcade.SpriteList[arcade.Sprite] = None
        self.pieces: arcade.SpriteList[Piece] = None
        self._highlights: arcade.SpriteList[arcade.Sprite] = None
        self._warnings: arcade.SpriteList[arcade.Sprite] = None

        ## Board will rotate until it reaches the target angle.
        self.perspective = chess.WHITE
        self.target_angle = 0
        self.angle = 0

        self.center = center
        self.origin = NamedPoint(center.x - BOARD_HALF, center.y - BOARD_HALF)

        ## Alpha value of the text.
        self.alpha = 0
        self.target_alpha = 255

        ## Events

        self._on_player_move = EventSource()
        self._on_board_undo = EventSource()

        self.create_board()
        self.create_labels()
        self.reset()

    def create_board(self):
        self.squares = arcade.ShapeElementList()
        self.squares.center_x = self.center.x
        self.squares.center_y = self.center.y

        # Create the board background
        self.texture = arcade.load_texture("assets/board.jpg")
        self.scale = BOARD_WIDTH / self.texture.width

        self.squares.append(
            arcade.create_rectangle_filled(
                0,
                0,
                BOARD_WIDTH,
                BOARD_WIDTH,
                COLOR_BOARD,
            )
        )

        # Calculate the center offset of a square
        centers = [x * SQUARE_SIZE + SQUARE_CENTER for x in range(-4, 4)]
        color_index = 0

        # Create the squares by file and rank (A1, A2, ... H8)
        for file in centers:
            color_index += 1
            for rank in centers:
                self.squares.append(
                    self._create_square(
                        NamedPoint(rank, file), Board.COLORS[color_index % 2]
                    )
                )
                color_index += 1

    def create_labels(self):
        self.labels = arcade.SpriteList()
        margin = BOARD_MARGIN / 2

        self.target_alpha = 255

        for x in range(0, 8):
            center = x * SQUARE_SIZE + SQUARE_CENTER
            if self.perspective == chess.BLACK:
                x = 7 - x

            self.labels.append(
                self._create_text_sprite(
                    str(x + 1),
                    NamedPoint(self.origin.x - margin, self.origin.y + center),
                    TEXT_COLOR,
                )
            )

            self.labels.append(
                self._create_text_sprite(
                    str(chr(x + 65)),
                    NamedPoint(self.origin.x + center, self.origin.y - margin),
                    TEXT_COLOR,
                )
            )

    def update_pieces(self):
        """Recreates the pieces according to the current board state."""
        self.pieces = arcade.SpriteList()
        for square, piece in self.chess_board.piece_map().items():
            self.pieces.append(
                Piece(
                    piece,
                    square,
                    self.center,
                    self.offset_of(square),
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

    def update(self, delta_time: float):
        self.rotate_board()
        self.animate_alpha()

    def draw(self):
        self.texture.draw_scaled(
            self.center.x, self.center.y, self.scale, self.squares.angle
        )
        self.squares.draw()
        self.labels.draw()
        self._highlights.draw()
        self.pieces.draw()
        self._warnings.draw()

    @property
    def on_player_move(self) -> EventSource:
        return self._on_player_move

    @property
    def on_board_undo(self) -> EventSource:
        return self._on_board_undo

    @property
    def width(self) -> int:
        return BOARD_WIDTH

    @property
    def height(self) -> int:
        return BOARD_WIDTH

    ############################
    # Coordinates
    ############################

    def offset_of(self, square: chess.Square) -> NamedPoint:
        """Returns the center of a square, relative to the center of the board."""
        rank = chess.square_rank(square) - 4  ## row
        file = chess.square_file(square) - 4  ## column

        return NamedPoint(
            SQUARE_SIZE * file + SQUARE_CENTER,
            SQUARE_SIZE * rank + SQUARE_CENTER,
        )

    def center_of(self, square: chess.Square) -> NamedPoint:
        """Returns the center of a square, relative to screen coordinates."""
        rank = chess.square_rank(square)  ## row
        file = chess.square_file(square)  ## column

        if self.perspective == chess.BLACK:
            rank = 7 - rank
            file = 7 - file

        return NamedPoint(
            self.origin.x + SQUARE_SIZE * file + SQUARE_CENTER,
            self.origin.y + SQUARE_SIZE * rank + SQUARE_CENTER,
        )

    def square_at(self, x: int, y: int) -> chess.Square:
        """Returns the square at the given screen coordinates."""
        file = (x - self.origin.x) // SQUARE_SIZE
        rank = (y - self.origin.y) // SQUARE_SIZE

        if file < 0 or rank < 0 or file > 7 or rank > 7:
            return None

        if self.perspective is chess.BLACK:
            rank = 7 - rank
            file = 7 - file

        return chess.square(file, rank)

    ############################
    # Perspective
    ############################

    def rotate_board(self):
        """Rotates the board and pieces by the given angle."""
        if self.angle == self.target_angle:
            return

        if self.angle < self.target_angle:
            self.angle += ROTATE_SPEED / 60  ## FPS

        LOG.info(f"Rotating board to {self.angle} degrees")

        self.squares.angle = self.angle
        angle_rad = math.radians(self.angle)
        for sprite in self.pieces:
            sprite.rotate(angle_rad)

    def set_perspective(self, player=chess.WHITE) -> None:
        """Sets the perspective of the board to the given player."""
        if player == self.perspective:
            return
        self.angle, self.target_angle = [
            (180, 360),
            (0, 180),
        ][self.perspective]
        self.perspective = player
        self.target_alpha = 0

    def toggle_perspective(self) -> None:
        """Swaps the perspective of the board."""
        self.set_perspective(not self.perspective)

    ############################
    # Moves
    ############################

    def reset_piece(self, piece: Piece) -> None:
        """Resets the piece to its original position."""
        piece.position = self.center_of(piece.square)
        self.update_highlights()

    def move_piece(self, piece: Piece, square: chess.Square) -> bool:
        """Moves a piece to the given square. Returns True if the move was valid."""
        if not self.is_valid_move(piece, square):
            # Return to original position.
            piece.position = self.center_of(piece.square)
            return False

        player = self.chess_board.turn
        self.chess_board.push(chess.Move(piece.square, square))
        self.set_perspective(self.chess_board.turn)
        self.update_pieces()

        # Look for warnings
        if self.chess_board.is_check():
            self.update_warnings(self.chess_board.checkers(), "check")
        else:
            self.update_warnings()

        self._on_player_move(player=player, move_uci=self.chess_board.peek().uci())
        return True

    def is_valid_move(self, piece: Piece, square: chess.Square) -> bool:
        """Returns True if the given move is valid."""
        return self.chess_board.is_legal(chess.Move(piece.square, square))

    def legal_moves(self, piece: Piece) -> List[chess.Square]:
        """Returns a list of legal moves for the given piece."""
        return [
            move.to_square
            for move in self.chess_board.legal_moves
            if move.from_square == piece.square
        ]

    def undo_move(self) -> None:
        """Undoes the last move and resets perspective."""
        if (len(self.chess_board.move_stack)) == 0:
            return

        self.chess_board.pop()
        self.set_perspective(self.chess_board.turn)
        self._on_board_undo(player=self.chess_board.turn)

    def show_attackers_of(self, x: int, y: int) -> None:
        """Highlights all squares that threaten the given square."""
        square = self.square_at(x, y)
        if square in self._warnings.extra:
            return

        attackers = self.chess_board.attackers(not self.chess_board.turn, square)
        self.update_warnings(attackers, "threat")

    ############################
    # Highlights
    ############################

    def highlight_square_at(self, x: int, y: int) -> None:
        """Highlights the square at the given coordinates."""
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
        """Returns a list of highlighted squares."""
        return self._highlights.extra

    def set_highlights(self, value: List[chess.Square]) -> None:
        """Sets the highlighted squares."""
        self.update_highlights(value)

    highlights = property(get_highlights, set_highlights)

    ############################
    # Fade In/Out
    ############################

    def animate_alpha(self):
        if self.alpha == self.target_alpha:
            return

        if self.alpha < self.target_alpha:
            self.alpha += ALPHA_SPEED / 60  ## FPS
        else:
            self.alpha -= ALPHA_SPEED / 60  ## FPS

        self.alpha = max(0, min(self.target_alpha, self.alpha))

        LOG.info(f"Animating alpha to {self.alpha}")

        for sprite in self.labels:
            sprite.alpha = self.alpha
        for sprite in self._highlights:
            sprite.alpha = self.alpha

        if self.alpha == self.target_alpha:
            self.create_labels()

    ############################
    # Private methods
    ############################

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
        text_sprite = arcade.create_text_sprite(
            text,
            center.x,
            center.y,
            font_color,
            font_size,
            anchor_x="center",
            anchor_y="center",
        )
        text_sprite.alpha = self.alpha
        return text_sprite
