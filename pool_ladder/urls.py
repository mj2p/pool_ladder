"""pool_ladder URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from pool_ladder import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i/', include('impersonate.urls')),

    path('accounts/', include('django_registration.backends.one_step.urls')),

    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', views.IndexView.as_view(), name='index'),
    path('play/<int:pk>', views.PlayMatch.as_view(), name='play_match'),

    path('player/<int:pk>', views.PlayerView.as_view(), name='player_detail'),
    path('player/<int:pk>/results', views.PlayerResultsDataTablesView.as_view(), name='player_results_datatable'),

    path('user/<int:pk>/update', views.UserNameUpdateView.as_view(), name='update_username'),

    path('match/<int:pk>', views.MatchView.as_view(), name='match_detail'),

    path('ladder/datatable', views.LadderDataTablesView.as_view(), name='ladder_datatable'),
    path('challenge/datatable', views.ChallengesDataTablesView.as_view(), name='challenge_datatable'),
    path('match/datatable', views.PlayedMatchesDataTablesView.as_view(), name='match_datatable')
]
