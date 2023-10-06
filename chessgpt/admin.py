from django.contrib.admin import ModelAdmin, TabularInline, register
from django.contrib.auth.admin import UserAdmin
from .models import Game, Move, ChatHistory


class MoveInline(TabularInline):
    model = Move
    extra = 1

class GameAdmin(ModelAdmin):
    model = Game
    list_display = ('name', 'owner', 'created_at', 'updated_at')
    list_filter = ('owner', 'created_at', 'updated_at')
    inlines = [MoveInline]

register(Game, GameAdmin)