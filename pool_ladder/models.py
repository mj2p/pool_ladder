from datetime import timedelta

import pygal
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Max, Min
from django.utils import timezone
from django.utils.timezone import now
from pandas.tseries.offsets import BDay
from pygal.style import CleanStyle


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rank = models.IntegerField(default=0)
    slack_id = models.CharField(max_length=255, blank=True, null=True)
    movement = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    @property
    def matches(self):
        """
        return the query set of matches that the user has played
        :return:
        """
        return Match.objects.filter(
            played__isnull=False
        ).filter(
            Q(opponent=self.user) | Q(challenger=self.user)
        )

    @property
    def is_available(self):
        """
        determine if this user has any open challenges or has played a match in the last 4 hours
        """
        if not self.has_open_challenge and not self.in_cool_down and self.active:
            return True

        return False

    @property
    def has_open_challenge(self):
        """
        return True if this user is in a match not yet played
        """
        return Match.objects.filter(
            played__isnull=True,
            declined=False
        ).filter(
            Q(challenger=self.user) | Q(opponent=self.user)
        ).count() > 0

    @property
    def last_played_match(self):
        """
        return the last match this user was involved in
        """
        return self.matches.order_by('played').last()

    @property
    def in_cool_down(self):
        """
        Determine if the player is in their cool down period
        """
        in_cool_down = False

        if self.last_played_match:
            in_cool_down = (now() - self.last_played_match.played) <= timedelta(hours=4)

        return in_cool_down

    @property
    def time_available(self):
        """
        Return the time the player will become available
        """
        if self.last_played_match:
            return self.last_played_match.played + timedelta(hours=4)
        return None

    @property
    def swag(self):
        active_profiles = UserProfile.objects.filter(active=True)
        swag = []

        if self.rank == active_profiles.aggregate(min_rank=Min('rank'))['min_rank']:
            swag.append('1f478')

        if self.rank == active_profiles.aggregate(max_rank=Max('rank'))['max_rank']:
            swag.append('1F4A9')

        if self.movement == 100:
            # user was balled
            swag.append('1F3B1')

        return swag

    def can_challenge(self, challenger):
        """
        determine if the provided user can challenge this user
        """
        try:
            return (
                    challenger.userprofile.rank > self.rank >= (challenger.userprofile.rank - 2)
                    and not self.has_open_challenge
                    and challenger.userprofile.is_available
            )
        except UserProfile.DoesNotExist:
            return False

    def can_decline(self):
        """
        User is able to decline if they have been challenged twice in a row (unless they are rank 1
        """
        can_decline = False

        if self.rank == 1:
            return can_decline

        # get the last 2 matches for this user
        matches = Match.objects.filter(Q(challenger=self.user) | Q(opponent=self.user)).order_by('-challenge_time')[:2]

        user_challenged_count = 0

        for match in matches:
            if match.declined:
                continue

            if match.opponent == self.user:
                user_challenged_count += 1

        if user_challenged_count == 2:
            can_decline = True

        return can_decline

    def update_rank(self, rank, balled=False):
        """
        Update the rank of this profile with the given rank.
        If balled is True set rank to bottom and move everyone else below rank up
        """
        if balled:
            # get current maximum rank
            max = UserProfile.objects.aggregate(max_rank=Max('rank'))
            self.rank = max['max_rank']

            # get all profiles above 'rank' (the losers rank) and move them up 1
            for profile in UserProfile.objects.filter(rank__gt=rank):
                profile.rank -= 1
                profile.save()

            # set movement to 100 (balled)
            self.movement = 100
            self.save()
            return

        self.movement = rank - self.rank
        self.rank = rank
        self.save()

    def get_rank_chart(self):
        """
        Use Pygal to generate a chart of the rank movements
        :return:
        """
        ranks = [(now(), self.rank)]

        for match in self.matches.order_by('-played'):
            if self.user == match.winner:
                ranks.insert(0, (match.played, match.winner_rank))
            else:
                ranks.insert(0, (match.played, match.loser_rank))

            if self.user == match.challenger:
                ranks.insert(0, (match.played, match.challenger_rank))
            else:
                ranks.insert(0, (match.played, match.opponent_rank))

        chart = pygal.DateTimeLine(
            title='Rank Movements',
            x_label_rotation=35,
            x_title='Date Played',
            y_title='Rank',
            range=(1, UserProfile.objects.aggregate(max_rank=Max('rank'))['max_rank']),
            inverse_y_axis=True,
            show_legend=False,
            truncate_label=-1,
            x_value_formatter=lambda dt: dt.strftime('%b. %d, %Y, %I:%M %p'),
            style=CleanStyle(
                font_family='googlefont:Raleway',
            ),
        )
        chart.add('', ranks)
        return chart.render_data_uri()

    @property
    def matches_won(self):
        """
        Return the number of matches won by this user
        """
        return Match.objects.filter(
            played__isnull=False
        ).filter(
            winner=self.user
        ).count()

    @property
    def matches_lost(self):
        """
        Return the number of matches lost by this user
        """
        return Match.objects.filter(
            played__isnull=False
        ).filter(
            loser=self.user
        ).count()

    @property
    def games_won(self):
        """
        return the number of games won by this user
        """
        return Game.objects.filter(winner=self.user).count()

    def __str__(self):
        return '{} #{}'.format(self.user, self.rank)

    class Meta:
        ordering = ['rank']

    def save(self, **kwargs):
        super().save(kwargs)

        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'send.users'
            }
        )


class Season(models.Model):
    date_started = models.DateTimeField(default=timezone.now)
    number = models.IntegerField(default=1)

    class Meta:
        ordering = ['-date_started']

    def __str__(self):
        return '{} <{}>'.format(self.number, self.date_started)


class Match(models.Model):
    challenge_time = models.DateTimeField(
        default=timezone.now
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    challenger = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='challenger_match'
    )
    opponent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='opponent_match'
    )
    winner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='winner_match',
        blank=True,
        null=True
    )
    loser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='loser_match',
        blank=True,
        null=True
    )
    challenger_rank = models.IntegerField(null=True, blank=True)
    opponent_rank = models.IntegerField(null=True, blank=True)
    winner_rank = models.IntegerField(null=True, blank=True)
    loser_rank = models.IntegerField(null=True, blank=True)
    played = models.DateTimeField(null=True, blank=True)
    pending = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)
    days_to_play = models.IntegerField(default=3)

    class Meta:
        ordering = ['-challenge_time']
        verbose_name_plural = "matches"

    def __str__(self):
        return '{}: {} vs {}'.format(self.challenge_time, self.challenger, self.opponent)

    def save(self, **kwargs):
        super().save(kwargs)

        if self.played:
            # played is set when results are entered so redraw the matches table
            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'send.matches'
                }
            )
            return

        # this is a new challenge
        async_to_sync(get_channel_layer().group_send)(
            'pool_ladder',
            {
                'type': 'send.challenges'
            }
        )

        # Notify the opponent of the challenge.
        # only if days_to_play is the default 3 otherwise new notifications will go out each time a day is added
        if self.days_to_play == 3 and not self.declined:
            if self.opponent.email:
                async_to_sync(get_channel_layer().send)(
                    'notifications',
                    {
                        'type': 'email',
                        'email': self.opponent.email,
                        'challenger': self.challenger.username,
                        'time_until': self.time_until.strftime('%Y-%m-%d %H:%M:%S')
                    }
                )

            async_to_sync(get_channel_layer().send)(
                'notifications',
                {
                    'type': 'slack',
                    'message': '{} You have been challenged to a {} match by {}.\n'
                               'You need to play the match by {} or you will forfeit'.format(
                                    (
                                        '<@{}>'.format(self.opponent.userprofile.slack_id)
                                        if self.opponent.userprofile.slack_id
                                        else self.opponent.username
                                    ),
                                    settings.LADDER_NAME,
                                    (
                                        '<@{}>'.format(self.challenger.userprofile.slack_id)
                                        if self.challenger.userprofile.slack_id
                                        else self.challenger.username
                                    ),
                                    self.time_until.strftime('%Y-%m-%d %H:%M:%S')
                               )
                }
            )

    def can_play(self, user):
        """
        Check that the user can enter results for this match
        """
        if user == self.opponent:
            return True

        if user == self.challenger:
            return True

        return False

    @property
    def loser_balled(self):
        for game in self.game_set.all():
            if game.balled == self.loser:
                return True

        return False

    @property
    def time_until(self):
        return self.challenge_time + BDay(self.days_to_play)

    def start_match(self, **kwargs):
        self.played = now()

        if not self.challenger_rank:
            self.challenger_rank = self.challenger.userprofile.rank

        if not self.opponent_rank:
            self.opponent_rank = self.opponent.userprofile.rank

        super().save(**kwargs)

        if self.game_set.count() == 0:
            for x in range(3):
                game = Game.objects.create(
                    index=x,
                    match=self
                )
                game.save()
                self.game_set.add(game)

    def set_winner_and_loser(self):
        game_wins = {'challenger': 0, 'opponent': 0}

        winner_rank = min(self.challenger_rank, self.opponent_rank)
        loser_rank = max(self.challenger_rank, self.opponent_rank)

        for game in self.game_set.all():
            # if a player is balled in any game they immediately lose the match
            if game.balled == self.challenger:
                self.winner = self.opponent
                self.opponent.userprofile.update_rank(winner_rank)
                self.winner_rank = self.opponent.userprofile.rank

                self.loser = self.challenger
                self.challenger.userprofile.update_rank(loser_rank, balled=True)
                self.loser_rank = self.challenger.userprofile.rank

                self.save()
                # we should let everyone know
                async_to_sync(get_channel_layer().send)(
                    'notifications',
                    {
                        'type': 'slack',
                        'message': '{} JUST GOT BALLED!'.format(
                                        (
                                            '<@{}>'.format(self.challenger.userprofile.slack_id)
                                            if self.challenger.userprofile.slack_id
                                            else self.challenger.username
                                        )
                                    )
                    }
                )
                return

            if game.balled == self.opponent:
                self.winner = self.challenger
                self.challenger.userprofile.update_rank(winner_rank)
                self.winner_rank = self.challenger.userprofile.rank

                self.loser = self.opponent
                self.opponent.userprofile.update_rank(loser_rank, balled=True)
                self.loser_rank = self.opponent.userprofile.rank

                self.save()
                # we should let everyone know
                async_to_sync(get_channel_layer().send)(
                    'notifications',
                    {
                        'type': 'slack',
                        'message': '{} JUST GOT BALLED!'.format(
                            (
                                '<@{}>'.format(self.opponent.userprofile.slack_id)
                                if self.opponent.userprofile.slack_id
                                else self.opponent.username
                            )
                        )
                    }
                )
                return

            # otherwise get the tally going
            if game.winner == self.challenger:
                game_wins['challenger'] += 1

            if game.winner == self.opponent:
                game_wins['opponent'] += 1

        # at this point it's down to a best of 3
        if game_wins['challenger'] >= 2:
            self.winner = self.challenger
            self.loser = self.opponent
        else:
            self.winner = self.opponent
            self.loser = self.challenger

        self.save()

        self.winner.userprofile.update_rank(winner_rank)
        self.winner_rank = self.winner.userprofile.rank

        self.loser.userprofile.update_rank(loser_rank)
        self.loser_rank = self.loser.userprofile.rank

        self.save()

        async_to_sync(get_channel_layer().send)(
            'notifications',
            {
                'type': 'slack',
                'message': '{} has beaten {}!'.format(
                    self.winner,
                    self.loser
                )
            }
        )

        return


class Game(models.Model):
    index = models.IntegerField(default=0)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    winner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='winner',
        blank=True,
        null=True
    )
    balled = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='balled',
        blank=True,
        null=True
    )

    def __str__(self):
        return '{} {}'.format(self.match, self.index)

    class Meta:
        ordering = ['match', 'index']

