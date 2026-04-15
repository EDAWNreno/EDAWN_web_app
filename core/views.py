from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone

from .models import Task, Goal
from .forms import RegisterForm, TaskStatusForm, GoalProgressForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    my_tasks = Task.objects.filter(assigned_to=user).exclude(
        status=Task.STATUS_COMPLETED
    ).order_by('due_date', '-priority')
    my_goals = Goal.objects.filter(user=user)
    recent_completed = Task.objects.filter(
        assigned_to=user, status=Task.STATUS_COMPLETED
    ).order_by('-completed_at')[:5]
    top_users = Task.leaderboard()[:5]

    context = {
        'my_tasks': my_tasks,
        'my_goals': my_goals,
        'recent_completed': recent_completed,
        'top_users': top_users,
        'total_tasks': Task.objects.filter(assigned_to=user).count(),
        'completed_tasks': Task.objects.filter(
            assigned_to=user, status=Task.STATUS_COMPLETED
        ).count(),
        'overdue_tasks': [t for t in my_tasks if t.is_overdue],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def task_list(request):
    status_filter = request.GET.get('status', '')
    tasks = Task.objects.filter(assigned_to=request.user)
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    context = {
        'tasks': tasks,
        'status_filter': status_filter,
        'status_choices': Task.STATUS_CHOICES,
    }
    return render(request, 'core/task_list.html', context)


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    if request.method == 'POST':
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            if task.status == Task.STATUS_COMPLETED and not task.completed_at:
                task.completed_at = timezone.now()
            task.save()
            messages.success(request, 'Task updated.')
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskStatusForm(instance=task)
    return render(request, 'core/task_detail.html', {'task': task, 'form': form})


@login_required
def task_complete(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    if request.method == 'POST':
        task.status = Task.STATUS_COMPLETED
        task.completed_at = timezone.now()
        task.save()
        messages.success(request, f'"{task.title}" marked as complete!')
    return redirect(request.POST.get('next', 'dashboard'))


@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'core/goal_list.html', {'goals': goals})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalProgressForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal progress updated.')
            return redirect('goal_detail', pk=goal.pk)
    else:
        form = GoalProgressForm(instance=goal)
    return render(request, 'core/goal_detail.html', {'goal': goal, 'form': form})


@login_required
def leaderboard(request):
    users = Task.leaderboard()
    total_tasks_by_user = {
        u.id: Task.objects.filter(assigned_to=u).count()
        for u in users
    }
    context = {
        'users': users,
        'total_tasks_by_user': total_tasks_by_user,
    }
    return render(request, 'core/leaderboard.html', context)
