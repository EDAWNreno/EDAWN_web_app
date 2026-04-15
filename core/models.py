from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count


class Task(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_tasks'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED

    @property
    def is_overdue(self):
        from django.utils import timezone
        if self.due_date and not self.is_completed:
            return self.due_date < timezone.now().date()
        return False

    @classmethod
    def leaderboard(cls):
        return (
            User.objects
            .annotate(completed_count=Count(
                'assigned_tasks',
                filter=models.Q(assigned_tasks__status=cls.STATUS_COMPLETED)
            ))
            .filter(completed_count__gt=0)
            .order_by('-completed_count')
        )


class Goal(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='goals'
    )
    target_value = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    @property
    def progress_percentage(self):
        if self.target_value == 0:
            return 0
        return min(100, int((self.current_value / self.target_value) * 100))

    @property
    def is_complete(self):
        return self.current_value >= self.target_value
