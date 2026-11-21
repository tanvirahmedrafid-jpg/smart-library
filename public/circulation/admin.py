from django.contrib import admin
from circulation.models import LibrarySettings, Loan, Reservation

@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    list_display = ('loan_period_days', 'max_active_loans', 'fine_per_day', 'renewal_limit')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('copy', 'member', 'issue_date', 'due_date', 'returned_at', 'fine_amount', 'fine_paid')
    list_filter = ('returned_at', 'fine_paid')
    search_fields = ('copy__copy_code', 'copy__book__title', 'member__name', 'member__member_code')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('book', 'member', 'request_date', 'status')
    list_filter = ('status',)
    search_fields = ('book__title', 'member__name')
