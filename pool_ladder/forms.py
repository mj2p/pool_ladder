from django import forms
from pool_ladder.models import Match


class MatchForm(forms.Form):
    game_0_winner = forms.ChoiceField(choices=[])
    game_0_balled = forms.ChoiceField(choices=[])

    game_1_winner = forms.ChoiceField(choices=[])
    game_1_balled = forms.ChoiceField(choices=[])

    game_2_winner = forms.ChoiceField(choices=[])
    game_2_balled = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        match_pk = kwargs.pop('match_pk', None)
        super().__init__(*args, **kwargs)

        if match_pk:
            try:
                match = Match.objects.get(pk=match_pk)
            except Match.DoesNotExist:
                return

            choices = [
                ('---', '---'),
                (match.challenger.pk, match.challenger.username),
                (match.opponent.pk, match.opponent.username)
            ]

            self.fields['game_0_winner'].choices = choices
            self.fields['game_0_balled'].choices = choices

            self.fields['game_1_winner'].choices = choices
            self.fields['game_1_balled'].choices = choices

            self.fields['game_2_winner'].choices = choices
            self.fields['game_2_balled'].choices = choices

    def clean(self):
        form_data = self.cleaned_data

        ####
        # GAME 0
        ####

        # game 0 needs a winner even if someone was balled
        if form_data['game_0_winner'] == '---':
            self._errors["game_0_winner"] = ["Game 0 needs a winner"]
            return form_data

        # the same player cannot be balled and win
        if form_data['game_0_winner'] == form_data['game_0_balled']:
            self._errors["game_0_balled"] = ["Same player can't be balled and win"]
            return form_data

        # we've checked that there is a winner
        # if someone is balled in the first game they loose the match
        if form_data['game_0_balled'] != '---':
            return form_data

        ####
        # GAME 1
        ####

        # game 1 needs a winner only if someone wasn't balled in game 0
        if form_data['game_1_winner'] == '---':
            self._errors["game_1_winner"] = ["Game 1 needs a winner"]
            return form_data

        # the same player cannot be balled and win
        if form_data['game_1_winner'] == form_data['game_1_balled']:
            self._errors["game_1_balled"] = ["Same player can't be balled and win"]
            return form_data

        # we've checked that there is a winner
        # if someone is balled in the second game they loose the match
        if form_data['game_1_balled'] != '---':
            return form_data

        ####
        # GAME 2
        ####

        # if the same player has won the first two matches we can return
        if form_data['game_0_winner'] == form_data['game_1_winner']:
            return form_data

        # if game 2 is the tie break, it needs a winner
        # tie break occurs when different players won the first two games
        #
        if form_data['game_2_winner'] == '---':
            self._errors["game_2_winner"] = ["Game 2 needs a winner"]
            return form_data

        # the same player cannot be balled and win
        if form_data['game_2_winner'] == form_data['game_2_balled']:
            self._errors["game_2_balled"] = ["Same player can't be balled and win"]
            return form_data

        # we've checked that there is a winner
        # if someone is balled in the second game they loose the match
        if form_data['game_2_balled'] != '---':
            return form_data

        return form_data
