import arcade
import arcade.gui
import chess
import logging

from typing import List

from classes.Board import Board
from classes.Piece import Piece
from classes.ChatGptApi import ApiMove, ApiError, ApiGameCreated, ChatGptApi
from classes.EventSource import EventSource

LOG = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(thread)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
arcade.configure_logging(logging.ERROR)

#####################################################################
# Constants
#####################################################################

SCREEN_TITLE = "Chess with ChatGPT"

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

CHAT_WIDTH = SCREEN_GRID_WIDTH * 18
CHAT_BOX_HEIGHT = SCREEN_GRID_HEIGHT * 2
CHAT_BUTTON_WIDTH = SCREEN_GRID_WIDTH * 3

#####################################################################
# Game Window
#####################################################################


class ChessGame(arcade.Window):
    """Main Window"""

    PLAYERS = ["Black", "White"]  # Maps to chess.BLACK and chess.WHITE

    def __init__(self, width, height, title):
        """Create the variables"""
        super().__init__(width, height, title)

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        LOG.info("Initializing game...")
        EventSource.set_dispatcher(self)

        self.api: ChatGptApi = ChatGptApi()

        self.chat_area = arcade.gui.UITextArea(
            width=CHAT_WIDTH,
            height=SCREEN_HEIGHT - CHAT_BOX_HEIGHT,
            font_size=12,
            text_color=arcade.color.WHITE,
        )

        self.chat_box = arcade.gui.UIInputText(
            width=CHAT_WIDTH - CHAT_BUTTON_WIDTH,
            height=CHAT_BOX_HEIGHT,
            font_size=12,
            text_color=arcade.color.WHITE,
            multiline=True,
        )

        self.chat_button = arcade.gui.UIFlatButton(
            width=CHAT_BUTTON_WIDTH,
            height=CHAT_BOX_HEIGHT,
            text="Send",
        )

        self.chat_button.on_click = lambda x: self.send_chat_text()

        h_box = arcade.gui.UIBoxLayout(vertical=False)
        h_box.add(self.chat_box)
        h_box.add(self.chat_button)

        v_box = arcade.gui.UIBoxLayout(vertical=True, align="left")
        v_box.add(self.chat_area)
        v_box.add(h_box.with_border(1, arcade.color.WHITE))

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                child=v_box,
                anchor_x="left",
                anchor_y="center",
                align_x=10,
                align_y=0,
            )
        )

        self.board: Board = Board(
            arcade.NamedPoint(
                CHAT_WIDTH + (SCREEN_WIDTH - CHAT_WIDTH) // 2, SCREEN_HEIGHT // 2
            )
        )
        self.dragging: Piece = None

    def setup(self):
        """Start the ball rolling"""
        self.api.hello()

    #####################################################################
    # Chat helpers
    #####################################################################

    def send_chat_text(self):
        """Send the chat box text"""
        message = self.chat_box.text.strip()
        if message != "":
            self.send_chat(message)
            self.chat_box.text = ""

    def append_chat(self, message: str):
        """Append a chat message"""
        if message == "":
            return
        self.chat_area.text += f"\n\n{message}"

    def send_chat(self, message: str):
        """Send a chat message"""
        if message == "":
            return
        self.api.chat(message)
        self.append_chat(message)

    #####################################################################
    # API event handlers
    #####################################################################

    def on_api_error(self, err: ApiError):
        LOG.info(f"Error message: {err.source} {err.status}")
        self.show_message_box(
            f"HTTP{err.status} received. {err.message}\nDid you start the ChessGPT service?",
            ["Quit", "OK"],
            lambda x: arcade.exit() if x == "Quit" else None,
        )

    def on_api_hello(self, data: str):
        """Display greeting from ChatGPT"""
        LOG.info(f"Hello received: {data}")
        try:
            self.append_chat(data)
            self.show_message_box(
                data,
                ["Sure!", "No thanks."],
                lambda x: self.api.create_game()
                if x == "Sure!"
                else self.show_message_box(
                    "Ok, bye!", callback=lambda x: arcade.exit()
                ),
            )
        except Exception as e:  # Fails if invoked from another thread.
            LOG.error(e)

    def on_api_created(self, data: ApiGameCreated):
        """Respond to updates to game state"""
        LOG.info(f"Game {data.id} created!")
        self.api.suggest_move()
        self.board.start(data.fen)

    def on_api_moved(self, data: ApiMove):
        LOG.info(f"Recorded {data.uci} for player{data.player}")
        ## TODO: Suggest only for ChatGPT's turn.
        self.api.suggest_move()

    def on_api_suggest(self, data: str):
        """Handle suggested move"""
        LOG.info(f"Suggested: {data}")
        ## Suggested moves aren't official until we execute them.
        try:
            # Check for valid UCI first
            _move = chess.Move.from_uci(data)
            if self.board.execute_move(data):
                self.api.make_move(data)
            else:
                self.send_chat("Oops, that move is illegal. Try again?")
        except Exception:
            # Otherwise, just display the chat message.
            self.append_chat(data)

    def on_api_chat(self, data: str):
        """Display with chat message"""
        LOG.info(f"Chat message: {data}")
        self.append_chat(data)

    #####################################################################
    # Game event handlers
    #####################################################################

    def on_player_move(self, player: int, move: chess.Move):
        LOG.info(f"Player {player} played {move} on board!")
        self.api.make_move(move)

    def on_board_undo(self, player: int, move: str):
        LOG.debug(f"Undoing last move...")
        self.api.chat(
            f"Oops. Ignore {move}. It's now {ChessGame.PLAYERS[player]}'s turn."
        )

    #####################################################################
    # Arcade event handlers
    #####################################################################

    def on_draw(self):
        """Draw everything"""
        arcade.start_render()
        self.board.draw()
        self.manager.draw()
        arcade.finish_render()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
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
        if key == arcade.key.ENTER:
            self.send_chat_text()
        if key == arcade.key.Z and modifiers & arcade.key.MOD_CTRL:
            self.board.undo_move
        elif key == arcade.key.ESCAPE:
            if self.dragging is not None:
                self.board.reset_piece(self.dragging)
                self.dragging = None
        elif key == arcade.key.Q:
            self.show_message_box(
                "Are you sure you want to quit?",
                ["Quit", "Cancel"],
                lambda x: arcade.exit() if x == "Quit" else None,
            )
        elif key == arcade.key.R:
            self.show_message_box(
                "Are you sure you want to restart the game?",
                ["Reset", "Cancel"],
                lambda x: self.board.start() if x == "Reset" else None,
            )
            self.board.reset()
        elif key == arcade.key.LEFT:
            self.board.toggle_perspective()

    def on_update(self, delta_time):
        """Movement and game logic"""
        self.board.update(delta_time)

    #####################################################################
    # Utility functions
    #####################################################################

    def show_message_box(
        self,
        message: str,
        buttons: List[str] = ["OK"],
        callback=lambda x: None,
    ):
        message_box = arcade.gui.UIMessageBox(
            width=360,
            height=240,
            message_text=message + "\n\n",
            callback=callback,
            buttons=buttons,
        )
        self.manager.add(message_box)


#####################################################################
# Custom Events (see EventSource.py)
#####################################################################

ChessGame.register_event_type("on_player_move")  # Sent when player moves a piece
ChessGame.register_event_type("on_board_undo")  # Sent when last turn was undone

ChessGame.register_event_type("on_api_hello")  # Sent when ChatGPT says hello
ChessGame.register_event_type("on_api_created")  # Sent after API creates game
ChessGame.register_event_type("on_api_moved")  # Sent after API registers a move
ChessGame.register_event_type("on_api_suggest")  # Sent when API returns a move
ChessGame.register_event_type("on_api_chat")  # Sent when API returns a chat
ChessGame.register_event_type("on_api_error")  # Sent when API returns error


def main():
    """Main function"""
    window = ChessGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
