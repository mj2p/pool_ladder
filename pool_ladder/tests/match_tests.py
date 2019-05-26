from django.test import TestCase
from pool_ladder.models import User, UserProfile, Game, Match


class MatchTestCase(TestCase):
    def setUp(self):
        self.opponent = User.objects.create(username='opponent')
        UserProfile.objects.create(
            user=self.opponent,
            rank=1
        )

        self.challenger = User.objects.create(username='challenger')
        UserProfile.objects.create(
            user=self.challenger,
            rank=2
        )

        self.other_player = User.objects.create(username='other_user')
        UserProfile.objects.create(
            user=self.other_player,
            rank=3
        )

    def test_rank_challenge_within_2(self):
        """
        Challenger is able to challenge opponent when rank is < 2 below
        """
        self.opponent.userprofile.rank = 1
        self.challenger.userprofile.rank = 2
        self.opponent.save()
        self.challenger.save()
        self.assertTrue(self.opponent.userprofile.can_challenge(self.challenger))

    def test_rank_challenge_greater_then_2(self):
        """
        Challenger is not able to challenge opponent when rank is > 2 below
        """
        self.opponent.userprofile.rank = 1
        self.challenger.userprofile.rank = 4
        self.opponent.save()
        self.challenger.save()
        self.assertFalse(self.opponent.userprofile.can_challenge(self.challenger))

    def test_cannot_challenge_when_opponent_already_challenged(self):
        """
        Challenger cannot challenge if opponent is not available
        """
        # Other_Player has already challenged Opponent so Challenger cannot challenge
        Match.objects.create(
            challenger=self.other_player,
            opponent=self.opponent,
            challenger_rank=self.other_player.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        self.assertFalse(self.opponent.userprofile.can_challenge(self.challenger))

    def test_cannot_challenge_when_opponent_already_challenging(self):
        """
        Challenger cannot challenge if opponent is not available
        """
        # Other_Player has already been challenged by Opponent so Challenger cannot challenge
        Match.objects.create(
            challenger=self.opponent,
            opponent=self.other_player,
            challenger_rank=self.opponent.userprofile.rank,
            opponent_rank=self.other_player.userprofile.rank
        )
        self.assertFalse(self.opponent.userprofile.can_challenge(self.challenger))

    def test_fail(self):
        self.assertTrue(False)
