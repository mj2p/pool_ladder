from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from pool_ladder.forms import MatchForm
from pool_ladder.models import Match


class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'pool_ladder/index.html', {'ladder_name': settings.LADDER_NAME})


class PlayMatch(LoginRequiredMixin, View):
    def get(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        form = MatchForm(match_pk=match.pk)
        return render(request, 'pool_ladder/play_match.html', {'match': match, 'form': form})

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)

        form = MatchForm(request.POST, match_pk=match.pk)

        if form.is_valid():
            ####
            # Start the match
            # this adds 3 games to the match and sets the winner and loser rank based on the participants

            match.start_match()

            ####
            # UPDATE GAME 0
            ####

            game_0 = match.game_set.get(index=0)

            try:
                game_0.winner = User.objects.get(pk=form.cleaned_data['game_0_winner'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            try:
                game_0.balled = User.objects.get(pk=form.cleaned_data['game_0_balled'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            game_0.save()

            ####
            # UPDATE GAME 1
            ####

            game_1 = match.game_set.get(index=1)

            try:
                game_1.winner = User.objects.get(pk=form.cleaned_data['game_1_winner'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            try:
                game_1.balled = User.objects.get(pk=form.cleaned_data['game_1_balled'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            game_1.save()

            ####
            # UPDATE GAME 2
            ####

            game_2 = match.game_set.get(index=2)

            try:
                game_2.winner = User.objects.get(pk=form.cleaned_data['game_2_winner'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            try:
                game_2.balled = User.objects.get(pk=form.cleaned_data['game_2_balled'])
            except User.DoesNotExist:
                pass
            except ValueError:
                pass

            game_2.save()

            ####
            # UPDATE MATCH
            ####

            match.set_winner_and_loser()
            match.save()

            return redirect('index')
        else:
            return render(request, 'pool_ladder/play_match.html', {'match': match, 'form': form})
