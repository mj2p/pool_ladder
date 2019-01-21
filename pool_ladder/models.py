from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Max
from django.utils.timezone import now
from pandas.tseries.offsets import BDay


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rank = models.IntegerField(default=0)
    slack_id = models.CharField(max_length=255, blank=True, null=True)
    movement = models.IntegerField(default=0)

    @property
    def is_available(self):
        """
        determine if this user has any open challenges
        """
        return Match.objects.filter(
            played__isnull=True
        ).filter(
            Q(challenger=self.user) | Q(opponent=self.user)
        ).count() == 0

    def can_challenge(self, challenger):
        """
        determine if the provided user can challenge this user
        """
        try:
            return (
                    challenger.userprofile.rank > self.rank >= (challenger.userprofile.rank - 2)
                    and self.is_available
                    and challenger.userprofile.is_available
            )
        except UserProfile.DoesNotExist:
            return False

    def update_rank(self, rank, balled=False):
        """
        Update the rank of this profile with the given rank.
        If balled is True set rank to bottom and move everyone else below rank up
        """
        if balled:

            # get all profiles below 'rank' (the losers rank) and move them up 1
            for profile in UserProfile.objects.filter(rank__gt=rank):
                profile.rank -= 1
                profile.save()

            # get current maximum rank
            max = UserProfile.objects.aggregate(max_rank=Max('rank'))
            self.rank = max['max_rank']

            # set movement to 100 (balled)
            self.movement = 100
            self.save()
            return

        self.movement = rank - self.rank
        self.rank = rank
        self.save()

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


class Match(models.Model):
    challenge_time = models.DateTimeField(
        auto_now_add=True
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

    class Meta:
        ordering = ['-challenge_time']
        verbose_name_plural = "matches"

    def __str__(self):
        return '{}: {} vs {}'.format(self.challenge_time, self.challenger, self.opponent)

    def save(self, **kwargs):
        super().save(kwargs)

        if self.played:
            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'send.matches'
                }
            )
        else:
            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'send.challenges'
                }
            )

            # Notify the opponent of the challenge
            if self.opponent.email:
                async_to_sync(get_channel_layer().group_send)(
                    'pool_ladder',
                    {
                        'type': 'email.notification',
                        'email': self.opponent.email,
                        'challenger': self.challenger.username,
                        'time_until': self.time_until.strftime('%Y-%m-%d %H:%M:%S')
                    }
                )

            async_to_sync(get_channel_layer().group_send)(
                'pool_ladder',
                {
                    'type': 'slack.notification',
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

    @property
    def loser_balled(self):
        for game in self.game_set.all():
            if game.balled == self.loser:
                return True

        return False

    @property
    def time_until(self):
        return self.challenge_time + BDay(3)

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
                return

            if game.balled == self.opponent:
                self.winner = self.challenger
                self.challenger.userprofile.update_rank(winner_rank)
                self.winner_rank = self.challenger.userprofile.rank

                self.loser = self.opponent
                self.opponent.userprofile.update_rank(loser_rank, balled=True)
                self.loser_rank = self.opponent.userprofile.rank

                self.save()
                return

            # otherwise get the tally going
            if game.winner == self.challenger:
                game_wins['challenger'] += 1

            if game.winner == self.opponent:
                game_wins['opponent'] += 1

        # at this point it's down to a best of 3
        if game_wins['challenger'] == 2:
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
