import arcade
import math


class RotatingSprite(arcade.Sprite):
    def __init__(
        self, filename, center: arcade.NamedPoint, offset: arcade.NamedPoint, scale=1
    ):
        super().__init__(filename, scale)
        self.position = (center.x + offset.x, center.y + offset.y)
        self.center = center
        self.offset = offset

    def rotate(self, angle_rad) -> None:
        rotated = self._rotate_point(self.offset, angle_rad)
        self.position = (self.center.x + rotated.x, self.center.y + rotated.y)

    def _rotate_point(
        self, offset: arcade.NamedPoint, angle_rad: float
    ) -> arcade.NamedPoint:
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        new_x = offset.x * cos_angle - offset.y * sin_angle
        new_y = offset.x * sin_angle + offset.y * cos_angle
        return arcade.NamedPoint(new_x, new_y)
