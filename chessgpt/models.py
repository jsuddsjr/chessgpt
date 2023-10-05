from django.db import models
from django.contrib.auth.models import User


class Game(models.Model):
    GAME_RESULTS = [(1, "1-0"), (2, "0-1"), (3, "1/2-1/2")]
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=200, null=True, blank=True, help_text="Event name"
    )
    result = models.IntegerField(
        choices=GAME_RESULTS, null=True, help_text="Game result"
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Move(models.Model):
    PLAYER_COLORS = [(1, "white"), (2, "black")]
    CHECK_TYPES = [("+", "check"), ("#", "checkmate")]
    PIECE_TYPES = [
        ("K", "king"),
        ("Q", "queen"),
        ("R", "rook"),
        ("B", "bishop"),
        ("N", "knight"),
        ("", "pawn"),
    ]
    CASTLE_TYPES = [("O-O", "kingside"), ("O-O-O", "queenside")]
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    piece = models.CharField(max_length=1, choices=PIECE_TYPES)
    capture = models.BooleanField(default=False)
    source = models.CharField(max_length=2)
    destination = models.CharField(max_length=2)
    checkType = models.CharField(
        max_length=1, choices=CHECK_TYPES, null=True, blank=True
    )
    promotion = models.CharField(
        max_length=1, choices=PIECE_TYPES, null=True, blank=True
    )
    castle = models.CharField(max_length=5, choices=CASTLE_TYPES, null=True, blank=True)
    comment = models.CharField(max_length=200, null=True, blank=True)
    color = models.IntegerField(choices=PLAYER_COLORS)
    elapsed = models.IntegerField(default=0, help_text="Time elapsed in seconds")
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.castle:
            return self.castle

        captured = "x" if self.capture else ""
        notes = f" {{{self.comment}}}" if self.comment else ""
        return f"{self.piece}{self.source}{captured}{self.destination}{self.checkType}{notes}"

    class Meta:
        ordering = ["-created"]


class ChatHistory(models.Model):
    CHAT_ROLES = [
        ("function", "Function"),
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    ]
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=CHAT_ROLES)
    fname = models.CharField(max_length=30, null=True)
    content = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    def toMessage(self):
        if self.role == "function":
            return {"role": "function", "name": self.fname, "content": self.content}
        return {"role": self.role, "content": self.content}

    class Meta:
        ordering = ["id"]
