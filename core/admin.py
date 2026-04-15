from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from .models import Task, Goal

# Re-register User with search_fields so autocomplete works in Task/Goal admin
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    search_fields = ('username', 'first_name', 'last_name', 'email')

admin.site.site_header = "EDAWN Administration"
admin.site.site_title = "EDAWN Admin"
admin.site.index_title = "Site Administration"


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'assigned_to', 'created_by', 'status', 'priority', 'due_date', 'created_at'
    )
    list_filter = ('status', 'priority', 'due_date')
    search_fields = ('title', 'description', 'assigned_to__username', 'assigned_to__email')
    autocomplete_fields = ('assigned_to', 'created_by')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    list_editable = ('status', 'priority')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'due_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assigned_to', 'created_by')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'current_value', 'target_value', 'progress_display', 'due_date')
    list_filter = ('due_date',)
    search_fields = ('title', 'description', 'user__username')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'user')
        }),
        ('Progress', {
            'fields': ('current_value', 'target_value', 'due_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Progress')
    def progress_display(self, obj):
        pct = obj.progress_percentage
        return f"{pct}% ({obj.current_value}/{obj.target_value})"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
