from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/complete/', views.task_complete, name='task_complete'),

    # Goals
    path('goals/', views.goal_list, name='goal_list'),
    path('goals/<int:pk>/', views.goal_detail, name='goal_detail'),

    # Leaderboard
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
