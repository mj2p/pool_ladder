import random
from math import ceil

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.template import Template, Context
from django.template.loader import get_template
from django.views import View
from django.views.generic import DetailView

from pool_ladder.forms import MatchForm
from pool_ladder.models import Match, UserProfile, Season


class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'pool_ladder/index.html')


class MatchView(DetailView):
    model = Match


class PlayerView(DetailView):
    model = UserProfile


class UserNameUpdateView(View):
    @staticmethod
    def post(request, pk):
        profile = get_object_or_404(UserProfile, pk=pk)
        profile.user.username = request.POST.get('username', profile.user.username)
        profile.user.save()
        profile.save()

        return redirect('player_detail', pk=pk)


class PlayMatch(LoginRequiredMixin, View):
    def get(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        form = MatchForm(match_pk=match.pk)
        return render(request, 'pool_ladder/play_match.html', {'match': match, 'form': form, 'games': [0, 1, 2]})

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        form = MatchForm(request.POST, match_pk=match.pk)

        if not match.can_play(request.user):
            messages.add_message(request, messages.ERROR, 'You are not authorised to play this match.')
            return render(request, 'pool_ladder/index.html')

        if match.played:
            messages.add_message(request, messages.ERROR, 'Results have already been entered for this match.')
            return render(request, 'pool_ladder/index.html')

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


class AddDayToMatch(View):
    @staticmethod
    def get(request, pk):
        match = get_object_or_404(Match, pk=pk)

        if request.user != match.opponent:
            messages.add_message(request, messages.ERROR, 'You are not authorised to add time to this match.')
            return render(request, 'pool_ladder/index.html')

        if match.days_to_play == settings.MAX_DAYS_TO_PLAY:
            messages.add_message(request, messages.ERROR, 'The match already has the maximum allowed time added.')
            return render(request, 'pool_ladder/index.html')

        match.days_to_play += 1
        match.save()
        messages.add_message(request, messages.INFO, 'A day has been added to the time.')
        return render(request, 'pool_ladder/index.html')


class DeclineMatch(View):
    @staticmethod
    def get(request, pk):
        match = get_object_or_404(Match, pk=pk)

        if request.user != match.opponent:
            messages.add_message(request, messages.ERROR, 'You are not authorised to decline this match.')
            return render(request, 'pool_ladder/index.html')

        if not match.opponent.userprofile.can_decline():
            messages.add_message(request, messages.ERROR, 'You cannot decline this match.')
            return render(request, 'pool_ladder/index.html')

        match.declined = True
        match.save()
        messages.add_message(request, messages.INFO, 'You have declined the match.')
        return render(request, 'pool_ladder/index.html')


def generic_data_tables_view(request, object, query_set, paginate=True):
    # get the basic parameters
    draw = int(request.GET.get('draw', 0))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 0))

    # handle a search term
    search = request.GET.get('search[value]', '')
    results_total = query_set.count()

    if search:
        # start with a blank Q object and add a query for every non-relational field attached to the model
        q_objects = Q()

        for field in object._meta.fields:
            if field.is_relation:
                continue
            kwargs = {'{}__icontains'.format(field.name): search}
            q_objects |= Q(**kwargs)

        query_set = query_set.filter(q_objects)

    # handle the ordering
    order_column_index = request.GET.get('order[0][column]')
    order_by = request.GET.get('columns[{}][name]'.format(order_column_index))
    order_direction = request.GET.get('order[0][dir]')

    if order_direction == 'desc':
        order_by = '-{}'.format(order_by)

    if order_by:
        query_set = query_set.order_by(order_by)

    # now we have our completed queryset. we can paginate it if requested
    if paginate:
        index = start + 1  # start is 0 based, pages are 1 based
        page = Paginator(
            query_set,
            length
        ).get_page(
            ceil(index / length)
        )

    return {
        'draw': draw,
        'recordsTotal': results_total,
        'recordsFiltered': query_set.count(),
        'data': page if paginate else query_set
    }


class LadderDataTablesView(LoginRequiredMixin, View):
    def get(self, request):
        data = generic_data_tables_view(request, UserProfile, UserProfile.objects.filter(active=True), paginate=False)
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        get_template('pool_ladder/fragments/user_rank.html').render({'profile': profile}),
                        get_template('pool_ladder/fragments/user_name.html').render({'profile': profile}),
                        get_template(
                            'pool_ladder/fragments/user_available.html'
                        ).render(
                            {
                                'profile': profile,
                                'can_challenge': profile.can_challenge(request.user)
                            }
                        )
                    ] for profile in data['data']
                ]
            }
        )


class ChallengesDataTablesView(LoginRequiredMixin, View):
    def get(self, request):
        data = generic_data_tables_view(
            request,
            Match,
            Match.objects.filter(played__isnull=True).filter(declined=False),
            paginate=False
        )
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        Template('{{ challenge.challenge_time }}').render(Context({'challenge': challenge})),
                        Template(
                            '<small>{{ challenge.time_until | timeuntil }}</small>'
                        ).render(
                            Context({'challenge': challenge})
                        ),
                        get_template(
                            'pool_ladder/fragments/challenge_challenger.html'
                        ).render(
                            {'challenge': challenge}
                        ),
                        get_template(
                            'pool_ladder/fragments/challenge_opponent.html'
                        ).render(
                            {'challenge': challenge}
                        ),
                        get_template(
                            'pool_ladder/fragments/challenge_action.html'
                        ).render(
                            {
                                'challenge': challenge,
                                'logged_in_user': request.user.username,
                                'max_days': challenge.days_to_play == settings.MAX_DAYS_TO_PLAY
                            }
                        )
                    ] for challenge in data['data']
                ]
            }
        )


class PlayedMatchesDataTablesView(LoginRequiredMixin, View):
    def get(self, request):
        data = generic_data_tables_view(
            request,
            Match,
            Match.objects.exclude(played__isnull=True).filter(declined=False)
        )
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        get_template('pool_ladder/fragments/match_link.html').render({'match': match}),
                        get_template('pool_ladder/fragments/match_winner.html').render({'match': match}),
                        get_template('pool_ladder/fragments/match_loser.html').render({'match': match})
                    ] for match in data['data']
                ]
            }
        )


class PlayerResultsDataTablesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        profile = get_object_or_404(UserProfile, pk=pk)
        data = generic_data_tables_view(request, Match, profile.matches)
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        get_template(
                            'pool_ladder/fragments/results_played.html'
                        ).render(
                            {
                                'match': match,
                                'user': profile.user
                            }
                        ),
                        get_template(
                            'pool_ladder/fragments/results_result.html'
                        ).render(
                            {
                                'match': match,
                                'user': profile.user
                            }
                        ),
                        get_template(
                            'pool_ladder/fragments/results_rank.html'
                        ).render(
                            {
                                'match': match,
                                'user': profile.user
                            }
                        )
                    ] for match in data['data']
                ]
            }
        )


class NewSeason(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        """
        This method will shuffle all player ranks and start a new season
        """
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        # create a new season
        # first get the latest season
        latest_season = Season.objects.all().first()
        Season.objects.create(number=latest_season.number + 1)

        # now we shuffle the ranks
        active_users = UserProfile.objects.filter(active=True).order_by('-rank')

        user_list = []

        for user in active_users:
            user_list.append({user.pk: user.rank})

        random.shuffle(user_list)

        new_rank = 1

        for user in user_list:
            profile = UserProfile.objects.get(pk=list(user.keys())[0])
            profile.rank = new_rank
            profile.save()

            new_rank += 1

        return redirect('index')


class MatchData(LoginRequiredMixin, View):
    @staticmethod
    def get(request, season):
        """
        Return serialized match data
        type can be json or anything else which defaults to csv
        """
        if season == 'all' or season == 0:
            matches = Match.objects.all()
        else:
            season_obj = get_object_or_404(Season, number=season)
            matches = Match.objects.filter(season=season_obj)

        data = [match.serialize() for match in matches]
        return JsonResponse(data, safe=False)



