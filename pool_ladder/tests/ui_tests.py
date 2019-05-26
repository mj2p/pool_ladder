from django.test import TestCase

from pool_ladder.models import User, UserProfile, Game, Match


class UITestCase(TestCase):
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

        self.other_player = User.objects.create_user(username='other_user', password='123456789')
        UserProfile.objects.create(
            user=self.other_player,
            rank=3
        )

    def test_match_cannot_be_edited(self):
        """
        Test that a match cannot be edited once results have been entered
        """
        # log in
        self.client.login(username='opponent', password='123456789')
        # create a match
        match = Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        # set the results
        response = self.client.post(
            '/play/{}'.format(match.pk),
            {
                'game_0_winner': self.opponent.pk,
                'game_0_balled': '---',
                'game_1_winner': self.opponent.pk,
                'game_1_balled': '---',
                'game_2_winner': self.opponent.pk,
                'game_2_balled': '---',
            }
        )
        self.assertEqual(response.url, '/')

        # try and set the results again
        response = self.client.post(
            '/play/{}'.format(match.pk),
            {
                'game_0_winner': self.challenger.pk,
                'game_0_balled': '---',
                'game_1_winner': self.challenger.pk,
                'game_1_balled': '---',
                'game_2_winner': self.challenger.pk,
                'game_2_balled': '---',
            }
        )
        # ensure we get a message returned
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'Results have already been entered for this match.')
