import arcade

class TitleView(arcade.View):
    """Class that manages the 'menu' view."""

    def __init__(self, center: arcade.NamedPoint):
        super().__init__()
        self.center = center

    def on_show_view(self):
        """Called when switching to this view."""
        texture = arcade.texture.load_texture(":resources:images/backgrounds/abstract_1.jpg")
        arcade.set_background_color(arcade.color.WHITE)


    def on_draw(self):
        """Draw the menu"""
        self.clear()
        arcade.draw_text(
            "Main Menu - Click to play",
            self.center.x,
            self.center.y,
            arcade.color.BLACK,
            font_size=30,
            anchor_x="center",
        )

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """Use a mouse press to advance to the 'game' view."""
        game_view = GameView()
        self.window.show_view(game_view)