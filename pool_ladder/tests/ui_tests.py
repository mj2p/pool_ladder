from django.conf import settings
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

        self.other_player = User.objects.create_user(username='other_player', password='123456789')
        UserProfile.objects.create(
            user=self.other_player,
            rank=3
        )

    def test_played_match_cannot_be_edited(self):
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

    def test_bad_player_cannot_play_match(self):
        # log in as other_player
        self.client.login(username='other_player', password='123456789')
        # create a match
        match = Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
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
        # ensure we get a message returned
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'You are not authorised to play this match.')

    def test_time_can_be_added_to_max(self):
        # create a match
        match = Match.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            challenger_rank=self.challenger.userprofile.rank,
            opponent_rank=self.opponent.userprofile.rank
        )
        self.assertEqual(match.days_to_play, 3)

        # log in as other_player
        self.client.login(username='other_player', password='123456789')
        response = self.client.get('/add-a-day/{}'.format(match.pk))
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'You are not authorised to add time to this match.')
        self.assertEqual(match.days_to_play, 3)

        # log in as opponent
        self.client.login(username='opponent', password='123456789')

        # add a day
        for x in range(settings.MAX_DAYS_TO_PLAY):
            current_days_to_play = match.days_to_play

            response = self.client.get('/add-a-day/{}'.format(match.pk))
            messages = list(response.context['messages'])
            self.assertEqual(len(messages), 1)

            if current_days_to_play >= settings.MAX_DAYS_TO_PLAY:
                self.assertEqual(messages[0].message, 'The match already has the maximum allowed time added.')
                match = Match.objects.get(pk=match.pk)
                self.assertEqual(match.days_to_play, settings.MAX_DAYS_TO_PLAY)
            else:
                self.assertEqual(messages[0].message, 'A day has been added to the time.')
                match = Match.objects.get(pk=match.pk)
                self.assertEqual(match.days_to_play, current_days_to_play + 1)

