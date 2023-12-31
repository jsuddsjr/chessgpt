import arcade
import chess
import chess.pgn

from pathlib import Path

from classes.RotatingSprite import RotatingSprite


class Piece(RotatingSprite):
    def __init__(
        self,
        piece: chess.Piece,
        square: chess.Square = None,
        center: arcade.NamedPoint = None,
        offset: arcade.NamedPoint = None,
    ):
        self.piece = piece
        self.square = square
        self.file_path = Path(
            f"assets/{self.piece.symbol().lower()}{chess.COLOR_NAMES[self.piece.color].lower()}.png"
        )
        super().__init__(str(self.file_path), center, offset)

    # def _get_texture(self) -> arcade.Texture:
    #     if self.file_path.exists() is False:
    #         self._convert_svg()
    #         return arcade.Texture.create_empty(self.file_path.name, (1, 1))
    #     return arcade.load_texture(self.file_path)

    # def _convert_svg(self):
    #     import chess.svg

    #     full_path = self.file_path.absolute().with_suffix(".svg")
    #     print(f"Saving SVG to {full_path}")

    #     svg_code = chess.svg.piece(self.piece)
    #     if full_path.parent.exists() is False:
    #         full_path.parent.mkdir(parents=True, exist_ok=True)
    #     file = open(full_path, "w")
    #     file.write(svg_code)
    #     file.close()
