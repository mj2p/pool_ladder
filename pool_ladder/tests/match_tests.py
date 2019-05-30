from django.test import TestCase
from pool_ladder.models import User, UserProfile, Game, Match


class MatchTestCase(TestCase):
    def setUp(self):
        self.opponent = User.objects.create_user(username='opponent', password='123456789')
        UserProfile.objects.create(
            user=self.opponent,
            rank=1
        )

        self.challenger = User.objects.create_user(username='challenger', password='123456789')
        UserProfile.objects.create(
            user=self.challenger,
            rank=2
        )

        self.other_player = User.objects.create_user(username='other_player', password='123456789')
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

    def test_user_can_decline_after_three_challenges(self):
        """
        Opponent is able to decline a match if they have been challenged twice in a row
        """
        self.opponent.userprofile.rank = 2
        self.opponent.save()
        self.assertFalse(self.opponent.userprofile.can_decline())

        # opponent gets challenged
        Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        self.assertFalse(self.opponent.userprofile.can_decline())

        # opponent is challenged again
        Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        self.assertTrue(self.opponent.userprofile.can_decline())

        # check that can_decline becomes False if user rank is 1
        self.opponent.userprofile.rank = 1
        self.opponent.save()
        self.assertFalse(self.opponent.userprofile.can_decline())

        # check that can_decline is false when user has challenged themselves
        self.opponent.userprofile.rank = 2
        self.opponent.save()
        self.assertTrue(self.opponent.userprofile.can_decline())
        match = Match.objects.create(
            challenger=self.opponent,
            opponent=self.other_player,
            challenger_rank=self.opponent.userprofile.rank,
            opponent_rank=self.other_player.userprofile.rank
        )
        self.assertFalse(self.opponent.userprofile.can_decline())

        # change the match so that it is declined
        match.challenger = self.challenger
        match.opponent = self.opponent
        match.declined = True
        self.assertFalse(self.opponent.userprofile.can_decline())

    def test_user_can_play_match(self):
        """
        Test that the user can play the match (use the match.can_play() function)
        """
        match = Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        self.assertTrue(match.can_play(self.opponent))
        self.assertTrue(match.can_play(self.challenger))
        self.assertFalse(match.can_play(self.other_player))

    def test_user_can_be_challenged_during_cool_down(self):
        # set the ranks
        self.opponent.userprofile.rank = 1
        self.challenger.userprofile.rank = 2
        self.other_player.userprofile.rank = 3

        # create a match
        match = Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        match.start_match()

        # make sure that both players are in cool down
        self.assertTrue(self.challenger.userprofile.in_cool_down)
        self.assertTrue(self.opponent.userprofile.in_cool_down)

        # now make sure that other_player can challenge either player
        self.assertTrue(self.opponent.userprofile.can_challenge(self.other_player))
        self.assertTrue(self.challenger.userprofile.can_challenge(self.other_player))
