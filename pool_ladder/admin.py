from django.contrib import admin

from pool_ladder.models import UserProfile, Match, Game, Season


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'rank', 'active', 'slack_id']
    raw_id_fields = ['user']
    list_editable = ['active', 'rank', 'slack_id']


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['date_started', 'number']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['challenge_time', 'played', 'challenger', 'opponent', 'challenger_rank', 'opponent_rank',
                    'winner_rank', 'loser_rank', 'winner', 'loser']
    raw_id_fields = ['challenger', 'opponent', 'winner', 'loser']
    list_editable = ['challenger_rank', 'opponent_rank', 'winner_rank', 'loser_rank']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['index', 'match', 'winner', 'balled']
    raw_id_fields = ['match', 'winner', 'balled']
