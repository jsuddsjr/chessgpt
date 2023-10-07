from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class Game(models.Model):
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    event = models.CharField(max_length=100, null=True, blank=True)
    white = models.CharField(max_length=100, null=True, blank=True)
    black = models.CharField(max_length=100, null=True, blank=True)
    round = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    outcome = models.CharField(max_length=100, null=True, blank=True)
    fen = models.CharField(max_length=100, help_text="Most recent FEN.")
    pgn = models.TextField(null=True, blank=True, help_text="PGN of game.")
    date = models.DateField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.event


class Move(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    ply = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Half-play count (even = white, odd = black).",
    )
    uci = models.CharField(max_length=10, help_text="Universal Chess Interface.")
    san = models.CharField(max_length=10, help_text="Standard Algebraic Notation.")
    fen = models.CharField(max_length=100, help_text="FEN prior to move.")

    def __str__(self):
        return self.san


class ChatHistory(models.Model):
    CHAT_ROLES = [
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    ]
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=CHAT_ROLES)
    content = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    def toMessage(self):
        return {"role": self.role, "content": self.content}
