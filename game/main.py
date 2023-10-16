import re
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

CHAT_BORDER = 2
CHAT_HEIGHT = SCREEN_HEIGHT - CHAT_BORDER * 10
CHAT_WIDTH = SCREEN_GRID_WIDTH * 18
CHAT_BOX_HEIGHT = SCREEN_GRID_HEIGHT * 3
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

        self.chat_box = arcade.gui.UIInputText(
            width=CHAT_WIDTH - CHAT_BUTTON_WIDTH,
            height=CHAT_BOX_HEIGHT,
            font_size=12,
            text_color=arcade.color.WHITE,
            multiline=True,
        )

        self.chat_box.caret.color = arcade.color.WHITE

        self.chat_button = arcade.gui.UIFlatButton(
            width=CHAT_BUTTON_WIDTH,
            height=CHAT_BOX_HEIGHT,
            text="Send",
        )

        self.chat_button.on_click = lambda x: self.send_chat_text()

        h_box = arcade.gui.UIBoxLayout(vertical=False, style={"spacing": 0})
        h_box.add(self.chat_box)
        h_box.add(self.chat_button)

        self.chat_area = arcade.gui.UITextArea(
            width=CHAT_WIDTH,
            height=SCREEN_HEIGHT - CHAT_BOX_HEIGHT,
            font_size=12,
            text_color=arcade.color.WHITE,
        )

        v_box = arcade.gui.UIBoxLayout(
            vertical=True, align="left", style={"spacing": 0}
        )
        v_box.add(
            h_box.with_border(CHAT_BORDER, arcade.color.WHITE).with_space_around(
                bottom=10
            )
        )
        v_box.add(self.chat_area)

        self.manager.add(
            arcade.gui.UIAnchorWidget(
                child=v_box,
                anchor_x="left",
                anchor_y="top",
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

        ## Add new messages at the top, so no scrolling is required.
        ## TODO: Add color to distinguish player messages from API messages.
        self.chat_area.text = f"{message}\n\n{self.chat_area.text}"

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
        """Display error messages from API"""
        LOG.info(f"Error message: {err.source} {err.status}")
        self.show_message_box(
            f"{err.source} returned '{err.message}' ({err.status})\nDid you start the ChessGPT service?",
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
        self.append_chat(f"Game {data.id} created!")
        self.api.suggest_move()
        self.board.start(data.fen)

    def on_api_moved(self, data: ApiMove):
        """Acknowledge move"""
        LOG.info(
            f"Recorded uci {data.uci}, ply {data.ply}, san {data.san}, player{int(data.turn)}"
        )

        self.append_chat(f"{ChessGame.PLAYERS[data.turn]} played {data.uci}")
        self.board.update_fen(data.fen)  ## Update the board state from server.

        if data.outcome:
            self.send_chat(data.outcome)
            self.show_message_box(
                data.outcome,
                ["Reset", "Quit"],
                lambda x: self.api.create_game() if x == "Reset" else arcade.exit(),
            )
        else:
            self.board.set_perspective(not data.turn)
            if data.turn == chess.BLACK:
                self.api.suggest_move()
            else:
                self.append_chat("Waiting for opponent...")

    def on_api_suggest(self, data: str):
        """Handle suggested move"""
        LOG.info(f"Suggested: {data}")

        turn = f"{ChessGame.PLAYERS[self.board.turn]}'s turn."

        ## Suggested moves aren't official until we execute them.
        try:
            # Check for valid UCI first
            _move = chess.Move.from_uci(data)
            if not self.board.execute_move(data):
                self.send_chat(f"Oops, move '{data}' isn't available. {turn}")
        except chess.InvalidMoveError:
            move = self.get_move_from_text(data)
            if move is not None:
                if not self.board.execute_move(move):
                    self.send_chat(f"Oops, {move} didn't work. {turn}")
            else:
                # Otherwise, just display the chat message.
                self.append_chat(data)
                self.append_chat(turn)

    def on_api_chat(self, data: str):
        """Display with chat message"""
        LOG.info(f"Chat message: {data}")
        self.append_chat(data)

        move = self.get_move_from_text(data)
        if move is not None:
            self.board.execute_move(move)

    def get_move_from_text(self, text: str) -> str:
        matches = re.findall(r"(([a-h][1-8]){2}[qbnr]?)", text)
        return matches[0][0] if len(matches) == 1 else None

    #####################################################################
    # Board event handlers
    #####################################################################

    def on_player_move(self, player: int, move: str):
        LOG.info(f"Player{player} played {move} on board")
        self.api.make_move(move)

    def on_board_undo(self, player: int, move: str):
        LOG.debug("Undoing last move...")
        self.api.chat(
            f"Oops. Ignore {move}. It's now {ChessGame.PLAYERS[player]}'s turn."
        )

    #####################################################################
    # Window event handlers
    #####################################################################

    def on_draw(self):
        """Draw everything"""
        arcade.start_render()
        self.board.draw()
        self.manager.draw()
        arcade.finish_render()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        """Move the piece, if dragging one."""
        if self.dragging is not None:
            self.dragging.position = (x, y)
            self.board.show_attackers_of(x, y)
        else:
            self.board.highlight_square_at(x, y)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """Pick up a piece, if available."""
        pieces: List[Piece] = arcade.get_sprites_at_point((x, y), self.board.pieces)
        if len(pieces) > 0 and pieces[0].piece.color == self.board.chess_board.turn:
            self.dragging = pieces[0]
            # Remove and re-add the piece to the list, so it is drawn last.
            self.board.pieces.remove(self.dragging)
            self.board.pieces.append(self.dragging)
            self.board.highlights = self.board.legal_moves(self.dragging)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        """Drop the piece, if we are holding one."""
        if self.dragging is not None:
            square = self.board.square_at(x, y)
            self.board.move_piece(self.dragging, square)
            self.dragging = None

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""

        ## Escape to cancel drag
        if key == arcade.key.ESCAPE:
            if self.dragging is not None:
                self.board.reset_piece(self.dragging)
                self.dragging = None

        elif modifiers & arcade.key.MOD_CTRL:
            ## Ctrl+ENTER to send text
            if key == arcade.key.ENTER:
                self.send_chat_text()
            ## Ctrl+Z to undo last move
            elif key == arcade.key.Z:
                self.board.undo_move

        elif modifiers & arcade.key.MOD_ALT:
            ## Alt+Q to quit
            if key == arcade.key.Q:
                self.show_message_box(
                    "Are you sure you want to quit?",
                    ["Quit", "Cancel"],
                    lambda x: arcade.exit() if x == "Quit" else None,
                )
            ## Alt+R to restart game
            elif key == arcade.key.R:
                self.show_message_box(
                    "Are you sure you want to start a new game?",
                    ["Reset", "Cancel"],
                    lambda x: self.api.create_game() if x == "Reset" else None,
                )

        elif modifiers & arcade.key.MOD_SHIFT:
            if key == arcade.key.LEFT:
                self.board.toggle_perspective()

    def on_update(self, delta_time):
        """Movement and game logic"""
        self.board.update(delta_time)

    def on_exit(self):
        """Called when user exits the application"""
        LOG.info("Exiting game...")

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
