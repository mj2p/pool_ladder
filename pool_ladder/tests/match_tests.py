from django.db.models import Max
from django.test import TestCase
from pool_ladder.models import User, UserProfile, Game, Match


def create_user(rank, active=True):
    user = User.objects.create_user(username='user_rank_{}'.format(rank), password='123456789')
    UserProfile.objects.create(
        user=user,
        rank=rank,
        active=active
    )


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

    def test_a_balling_does_all_the_right_things(self):
        # create loads of users
        for x in range(20):
            rank = x + 1
            create_user(rank)

        # create a load of matches
        opponent_rank = 1
        challenger_rank = 2

        while challenger_rank <= 20:
            Match.objects.create(
                challenger=User.objects.get(username='user_rank_{}'.format(challenger_rank)),
                opponent=User.objects.get(username='user_rank_{}'.format(opponent_rank)),
                challenger_rank=challenger_rank,
                opponent_rank=opponent_rank
            )

            opponent_rank += 2
            challenger_rank += 2

        # the third match results in a balling
        third_match = Match.objects.get(pk=3)
        third_match.start_match()

        game_0 = third_match.game_set.get(index=0)
        game_0.winner = User.objects.get(username='user_rank_5')
        game_0.balled = User.objects.get(username='user_rank_6')
        game_0.save()

        third_match.set_winner_and_loser()
        third_match.save()

        # user ranks should have altered accordingly
        self.assertEqual(User.objects.get(username='user_rank_6').userprofile.rank, 20)

        for user in User.objects.all():
            username_parts = user.username.split('_')

            if len(username_parts) < 3:
                continue

            original_rank = int(username_parts[2])

            if original_rank < 6:
                # players ranked higher than the balled player stay the same
                self.assertEqual(user.userprofile.rank, original_rank)

            if original_rank == 6:
                # balled player is balled
                self.assertEqual(user.userprofile.rank, 20)

            if original_rank > 6:
                # players ranked lower than the balled player all move up one
                self.assertEqual(user.userprofile.rank, original_rank-1)

        # we should also check the waiting match ranks

        for match in Match.objects.filter(played__isnull=True):
            opponent_original_rank = int(match.opponent.username.split('_')[2])
            challenger_original_rank = int(match.challenger.username.split('_')[2])
            
            # do the opponent
            if opponent_original_rank < 6:
                # players ranked higher than the balled player stay the same
                self.assertEqual(match.opponent_rank, opponent_original_rank)

            if opponent_original_rank == 6:
                # balled player is balled
                self.assertEqual(match.opponent_rank, 20)

            if opponent_original_rank > 6:
                # players ranked lower than the balled player all move up one
                self.assertEqual(match.opponent_rank, opponent_original_rank-1)
            
            # then the challenger
            if challenger_original_rank < 6:
                # players ranked higher than the balled player stay the same
                self.assertEqual(match.challenger_rank, challenger_original_rank)

            if challenger_original_rank == 6:
                # balled player is balled
                self.assertEqual(match.challenger_rank, 20)

            if challenger_original_rank > 6:
                # players ranked lower than the balled player all move up one
                self.assertEqual(match.challenger_rank, challenger_original_rank-1)

    def test_an_inactive_user_does_not_affect_a_balling(self):
        # create loads of users with a couple inactive
        for x in range(20):
            rank = x + 1
            create_user(rank, (rank < 18))

        # create a match
        match = Match.objects.create(
            challenger=User.objects.get(username='user_rank_5'),
            opponent=User.objects.get(username='user_rank_3'),
            challenger_rank=5,
            opponent_rank=3
        )

        # the match results in a balling
        match.start_match()

        game_0 = match.game_set.get(index=0)
        game_0.winner = User.objects.get(username='user_rank_5')
        game_0.balled = User.objects.get(username='user_rank_3')
        game_0.save()

        match.set_winner_and_loser()
        match.save()

        # make sure the balled players rank is
        self.assertEqual(
            User.objects.get(username='user_rank_3').userprofile.rank,
            UserProfile.objects.filter(active=True).aggregate(max_rank=Max('rank'))['max_rank']
        )
