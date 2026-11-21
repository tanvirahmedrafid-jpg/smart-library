from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from catalog.models import Book, BookCopy
from accounts.models import MemberProfile

class LibrarySettings(models.Model):
    loan_period_days = models.PositiveIntegerField(default=14, help_text="Default days allowed for a book loan")
    max_active_loans = models.PositiveIntegerField(default=3, help_text="Maximum active books per member")
    fine_per_day = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('5.00'), help_text="Fine rate per overdue day in BDT")
    renewal_limit = models.PositiveIntegerField(default=1, help_text="Max times a member can renew a loan")

    # Demand Analytics Weights (Formula: D = wB*B + wR*R + wS*S + wQ*Q)
    weight_borrowing = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.40'), help_text="Weight for borrowing counts (default 0.40)")
    weight_reservation = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.25'), help_text="Weight for reservation counts (default 0.25)")
    weight_survey = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.20'), help_text="Weight for student survey interest (default 0.20)")
    weight_search = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.15'), help_text="Weight for catalog searches (default 0.15)")
    shortage_threshold_demand = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('50.00'), help_text="Demand score above which shortage is flagged")

    class Meta:
        verbose_name = "Library Setting"
        verbose_name_plural = "Library Settings"

    def __str__(self):
        return f"Settings (Loan: {self.loan_period_days}d, Max: {self.max_active_loans}, Fine: {self.fine_per_day} BDT/day)"

    @classmethod
    def get_settings(cls):
        setting, _ = cls.objects.get_or_create(id=1)
        return setting

class Loan(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active Loan'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    ]

    copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name='loans')
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='loans')
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_loans')
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    fine_paid = models.BooleanField(default=False)
    renewal_count = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-issue_date', '-id']

    def __str__(self):
        return f"{self.copy.book.title} ({self.copy.copy_code}) -> {self.member.name}"

    def save(self, *args, **kwargs):
        if not self.due_date:
            settings = LibrarySettings.get_settings()
            self.due_date = timezone.localdate() + timedelta(days=settings.loan_period_days)
        super().save(*args, **kwargs)

    @property
    def is_returned(self):
        return self.returned_at is not None

    @property
    def is_overdue(self):
        if self.is_returned:
            return self.returned_at.date() > self.due_date
        return timezone.localdate() > self.due_date

    @property
    def overdue_days(self):
        if self.is_returned:
            delta = self.returned_at.date() - self.due_date
        else:
            delta = timezone.localdate() - self.due_date
        return max(0, delta.days)

    def calculate_current_fine(self):
        settings = LibrarySettings.get_settings()
        return Decimal(self.overdue_days) * settings.fine_per_day

    def return_book(self):
        now = timezone.now()
        self.returned_at = now
        self.fine_amount = self.calculate_current_fine()
        self.save()
        # Update copy status to available
        self.copy.status = 'available'
        self.copy.save()

    def renew_loan(self):
        settings = LibrarySettings.get_settings()
        if self.renewal_count >= settings.renewal_limit:
            return False, f"Maximum renewal limit ({settings.renewal_limit}) reached."
        if self.is_overdue:
            return False, "Overdue loans cannot be renewed. Please return the book and settle fines."
        
        self.due_date = self.due_date + timedelta(days=settings.loan_period_days)
        self.renewal_count += 1
        self.save()
        return True, f"Renewed successfully! New due date: {self.due_date}"

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('notified', 'Ready for Pickup'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='reservations')
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-request_date']

    def __str__(self):
        return f"Reservation: {self.book.title} for {self.member.name}"
