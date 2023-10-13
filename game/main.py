import arcade
import logging

from typing import List

from classes.Board import Board
from classes.Piece import Piece
from classes.Game import Game

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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


class ChessGame(arcade.Window):
    """Main Window"""

    def __init__(self, width, height, title):
        """Create the variables"""
        super().__init__(width, height, title)

        self.game: Game = Game()
        self.board: Board = None
        self.dragging: Piece = None

        self.messages: arcade.SpriteList = arcade.SpriteList()

    def setup(self):
        """Set up everything with the game"""
        center = arcade.NamedPoint(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        error = self.game.create_game()
        self.board = Board(self.game.fen, center, SPRITE_SCALING_TILES)

        if error:
            self.messages.append(
                arcade.create_text_sprite(
                    error,
                    center.x,
                    center.y,
                    arcade.color.BLUSH,
                    15.0,
                    align="center",
                    anchor_x="center",
                )
            )

    def on_draw(self):
        """Draw everything"""
        arcade.start_render()
        self.clear()
        self.board.draw()
        self.messages.draw()
        arcade.finish_render()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        LOG.debug(f"Mouse motion: {x}, {y}, {dx}, {dy}")
        if self.dragging is not None:
            self.dragging.position = (x, y)
            self.board.show_attackers_of(x, y)
        else:
            self.board.highlight_square_at(x, y)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        messages = arcade.get_sprites_at_point((x, y), self.messages)
        if messages:
            self.messages.remove(messages[0])
            return

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


def main():
    """Main function"""
    window = ChessGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
