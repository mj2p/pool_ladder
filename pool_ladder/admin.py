from django.contrib import admin

from pool_ladder.models import UserProfile, Match, Game


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'rank']
    raw_id_fields = ['user']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['challenge_time', 'challenger', 'opponent', 'challenger_rank', 'opponent_rank', 'winner', 'loser']
    raw_id_fields = ['challenger', 'opponent', 'winner', 'loser']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['index', 'match', 'winner', 'balled']
    raw_id_fields = ['match', 'winner', 'balled']