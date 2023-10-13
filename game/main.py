import arcade
import arcade.gui
import chess
import logging
import threading

from typing import List

from classes.Board import Board
from classes.Piece import Piece
from classes.ChatGptApi import ChatGptApi
from classes.EventSource import EventSource

LOG = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(thread)d %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
arcade.configure_logging(logging.ERROR)

#####################################################################
# Constants
#####################################################################

SCREEN_TITLE = "Chess with ChatGPT-3"

# How big are our image tiles?
SPRITE_IMAGE_SIZE = 128

# Scale sprites up or down
SPRITE_SCALING_PLAYER = 0.5
SPRITE_SCALING_TILES = 0.5

# Scaled sprite size for tiles
SPRITE_SIZE = int(SPRITE_IMAGE_SIZE * SPRITE_SCALING_PLAYER)

# Size of grid to show on screen, in number of tiles
SCREEN_GRID_WIDTH = 25
SCREEN_GRID_HEIGHT = 15

# Size of screen to show, in pixels
SCREEN_WIDTH = SPRITE_SIZE * SCREEN_GRID_WIDTH
SCREEN_HEIGHT = SPRITE_SIZE * SCREEN_GRID_HEIGHT


#####################################################################
# Game Window
#####################################################################


class ChessGame(arcade.Window):
    """Main Window"""

    def __init__(self, width, height, title):
        """Create the variables"""
        super().__init__(width, height, title)
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        LOG.warning("Initializing game...")
        EventSource.set_dispatcher(self)

        # self.v_box = arcade.gui.UIBoxLayout()
        # text_area = arcade.gui.UITextArea(height=SCREEN_HEIGHT, width=300)
        # self.v_box.add(text_area)

        self.api: ChatGptApi = ChatGptApi()
        self.board: Board = None
        self.dragging: Piece = None

    def setup(self):
        """Set up everything with the game"""
        center = arcade.NamedPoint(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.board = Board(self.api.fen, center, SPRITE_SCALING_TILES)
        self.api.hello()

    def on_error_message(self, event: str, status: int):
        LOG.warning(f"Error message: {event} {status}")
        self.show_message_box(
            f"HTTP{status} received from {event}. Is the service running?",
            ["Quit"],
            lambda x: arcade.close_window(),
        )

    def on_hello(self, data: str):
        """Open message box with hello message"""
        LOG.warning(f"Hello received: {data}")
        try:
            self.show_message_box(
                data,
                ["Sure!", "Quit"],
                lambda x: arcade.close_window()
                if x == "Quit"
                else self.api.create_game(),
            )
        except Exception as e:
            LOG.error(e)

    def on_suggest_move(self, event: str, data: str):
        """Open message box with suggested move"""
        LOG.warning(f"Suggested move: {data}")
        self.board.execute_move(data)

    def on_api_update(self, event: str, data: dict):
        """Update the game state"""
        LOG.warning(f"Event {event} received!")
        match event:
            case "create_game":
                self.show_message_box(data, ["OK"])
                self.api.suggest_move()
            case "make_move":
                self.show_message_box(data, ["OK"])
                self.api.suggest_move()
            case "chat":
                self.show_message_box(data, ["OK"])

    def on_player_move(self, player: int, move: str):
        LOG.warning(f"Player {player} played {move}!")
        if player == chess.BLACK:
            self.api.make_move(move)

        else:
            self.api.chat("I played this move for you: " + move)

    def on_draw(self):
        """Draw everything"""
        arcade.start_render()
        self.board.draw()
        self.manager.draw()
        arcade.finish_render()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        LOG.debug(f"Mouse motion: {x}, {y}, {dx}, {dy}")
        if self.dragging is not None:
            self.dragging.position = (x, y)
            self.board.show_attackers_of(x, y)
        else:
            self.board.highlight_square_at(x, y)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        pieces: List[Piece] = arcade.get_sprites_at_point((x, y), self.board.pieces)
        if len(pieces) > 0 and pieces[0].piece.color == self.board.chess_board.turn:
            self.dragging = pieces[0]
            # Remove and re-add the piece to the list, so it is drawn last.
            self.board.pieces.remove(self.dragging)
            self.board.pieces.append(self.dragging)
            self.board.highlights = self.board.legal_moves(self.dragging)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        if self.dragging is not None:
            square = self.board.square_at(x, y)
            self.board.move_piece(self.dragging, square)
            self.dragging = None

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""
        if key == arcade.key.Z and modifiers & arcade.key.MOD_CTRL:
            self.board.undo_move
        elif key == arcade.key.ESCAPE:
            if self.dragging is not None:
                self.board.reset_piece(self.dragging)
                self.dragging = None
        elif key == arcade.key.Q:
            arcade.close_window()
        elif key == arcade.key.R:
            self.board.reset()
        elif key == arcade.key.LEFT:
            self.board.toggle_perspective()

    def on_update(self, delta_time):
        """Movement and game logic"""
        self.board.update(delta_time)

    def show_message_box(
        self,
        message: str,
        buttons: List[str] = ["Cancel", "OK"],
        callback=lambda x: None,
    ):
        message_box = arcade.gui.UIMessageBox(
            width=300,
            height=200,
            message_text=message,
            callback=callback,
            buttons=buttons,
        )
        self.manager.add(message_box)


ChessGame.register_event_type("on_player_move")  # Sent when player moves a piece
ChessGame.register_event_type("on_api_update")  # Sent when API receives data
ChessGame.register_event_type("on_error_message")  # Sent when API returns error
ChessGame.register_event_type("on_chat_message")  # Sent when API returns a chat
ChessGame.register_event_type("on_suggest_move")  # Sent when API returns a move
ChessGame.register_event_type("on_board_undo")  # Sent when last turn was undone
ChessGame.register_event_type("on_hello")  # Sent when ChatGPT says hello


def main():
    """Main function"""
    window = ChessGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
