import arcade
from typing import List
from classes.Board import Board
from classes.Piece import Piece


SCREEN_TITLE = "Chess with Chat GPT-3"

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

        # Starting location of player
        self.x = 100
        self.y = 100

        self.board: Board = Board()
        self.dragging: Piece = None

        self.setup()

    def setup(self):
        """Set up everything with the game"""
        self.board.center(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def on_draw(self):
        """Draw everything"""
        self.clear()
        arcade.start_render()
        self.board.draw()
        ## arcade.draw_circle_filled(self.x, self.y, 25, arcade.color.BLUE)
        arcade.finish_render()

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        if self.dragging is not None:
            self.dragging.position = (x, y)
            self.board.show_attackers_of(x, y)
        else:
            self.board.highlight_square_at(x, y)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        piece_list: List[Piece] = arcade.get_sprites_at_point((x, y), self.board.pieces)
        if (
            len(piece_list) > 0
            and piece_list[0].piece.color == self.board.chess_board.turn
        ):
            self.dragging = piece_list[0]
            self.board.highlights = self.board.legal_moves(self.dragging)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        if self.dragging is not None:
            square = self.board.square_at(x, y)
            self.board.move_piece(self.dragging, square)
            self.dragging = None

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""
        if key == arcade.key.ESCAPE:
            arcade.close_window()
        elif key == arcade.key.R:
            self.board.reset()

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key."""
        pass

    def on_update(self, delta_time):
        """Movement and game logic"""
        pass


def main():
    """Main function"""
    window = ChessGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
