from django.contrib import admin
from accounts.models import MemberProfile, SecurityAuditLog

@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_code', 'role', 'department', 'status', 'joined_date')
    list_filter = ('role', 'status', 'department')
    search_fields = ('name', 'member_code', 'email', 'phone')
    ordering = ('name',)

@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'ip_address', 'details')
    list_filter = ('action', 'timestamp')
    search_fields = ('action', 'user__username', 'ip_address', 'details')
    readonly_fields = ('timestamp', 'action', 'user', 'ip_address', 'details')
