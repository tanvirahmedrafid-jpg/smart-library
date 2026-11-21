from django.db import models
from django.contrib.auth.models import User

class MemberProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student / Member'),
        ('librarian', 'Librarian'),
        ('admin', 'Administrator'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile', null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    member_code = models.CharField(max_length=30, unique=True, help_text="e.g. STU-2024-001 or LIB-01")
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=25, blank=True)
    department = models.CharField(max_length=100, default='Software Engineering')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    joined_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.member_code}) - {self.get_role_display()}"

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_librarian(self):
        return self.role == 'librarian' or (self.user and (self.user.is_staff or self.user.is_superuser))

    @property
    def is_admin(self):
        return self.role == 'admin' or (self.user and self.user.is_superuser)

    @property
    def active_loans_count(self):
        return self.loans.filter(returned_at__isnull=True).count()

    def can_borrow(self, max_allowed=3):
        if self.status != 'active':
            return False, "Membership status is inactive or suspended."
        if self.active_loans_count >= max_allowed:
            return False, f"Maximum loan limit ({max_allowed} books) reached."
        return True, "Eligible to borrow."


class SecurityAuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN_SUCCESS', 'Successful Login'),
        ('LOGIN_FAILED', 'Failed Login Attempt'),
        ('LOGOUT', 'User Logout'),
        ('PASSWORD_RESET', 'Password Reset by Admin'),
        ('ROLE_CHANGE', 'Role Changed'),
        ('STATUS_CHANGE', 'Account Status Changed'),
        ('DB_BACKUP', 'Database Backup Downloaded'),
        ('SETTINGS_UPDATE', 'System Settings Updated'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor = self.user.username if self.user else 'Anonymous'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.action} by {actor}"


def log_security_event(request, action, details, user=None):
    """Helper to record security audit trail with client IP."""
    try:
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        target_user = user if user else (request.user if request and request.user.is_authenticated else None)

        SecurityAuditLog.objects.create(
            user=target_user,
            action=action,
            ip_address=ip,
            details=details
        )
    except Exception as e:
        print(f"Error logging security event: {e}")
