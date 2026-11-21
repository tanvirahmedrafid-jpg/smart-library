import csv
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.conf import settings

from catalog.models import Book, BookCopy, Category
from circulation.models import Loan, Reservation, LibrarySettings
from accounts.models import MemberProfile, SecurityAuditLog, log_security_event
from accounts.views import is_staff_or_librarian, is_admin_user
from smart_ai.models import SurveyResponse
from smart_ai.recommender import get_smart_recommendations
from smart_ai.analytics import get_overdue_risk_analysis, get_book_demand_analytics

@login_required
def member_dashboard_view(request):
    """
    Dedicated Student / Member Workspace.
    Protected strictly for logged-in students.
    """
    profile = getattr(request.user, 'member_profile', None)
    if not profile:
        profile = MemberProfile.objects.create(
            user=request.user,
            member_code=f"STU-{request.user.id:04d}",
            name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            role='student'
        )

    # Handle Student Survey Submission
    if request.method == 'POST' and request.POST.get('action') == 'submit_survey':
        cat_id = request.POST.get('preferred_category')
        unmet = request.POST.get('unmet_subject', '').strip()
        freq = request.POST.get('unavailable_frequency', 'sometimes')
        satisfaction = int(request.POST.get('satisfaction_score', 4))
        wants_rec = request.POST.get('wants_recommendations') == '1'
        suggested = request.POST.get('suggested_title', '').strip()
        comments = request.POST.get('suggestions', '').strip()

        pref_cat = Category.objects.filter(pk=cat_id).first() if cat_id else None

        SurveyResponse.objects.create(
            student=profile,
            preferred_category=pref_cat,
            unmet_subject=unmet,
            unavailable_frequency=freq,
            satisfaction_score=satisfaction,
            wants_recommendations=wants_rec,
            suggested_title=suggested,
            suggestions=comments
        )
        messages.success(request, "Thank you! Your survey response has been recorded and factored into library demand analytics.")
        return redirect('member_dashboard')

    today = timezone.localdate()
    loans = Loan.objects.filter(member=profile, returned_at__isnull=True).select_related('copy__book')
    history = Loan.objects.filter(member=profile, returned_at__isnull=False).select_related('copy__book').order_by('-returned_at')[:10]

    # Precalculate helpers
    due_soon_count = 0
    total_fine = Decimal('0.00')

    for l in loans:
        l.copy.book.cover_style = l.copy.book.cover_theme.replace('cover-', '')
        days_left = (l.due_date - today).days
        if days_left <= 7:
            due_soon_count += 1
        if l.is_overdue:
            total_fine += l.calculate_current_fine()

    stats = {
        'active_loans': loans.count(),
        'due_soon': due_soon_count,
        'outstanding_fine': f"{total_fine:.2f}",
    }

    ai_recommendations = get_smart_recommendations(profile, limit=4)
    for b in ai_recommendations:
        b.cover_style = b.cover_theme.replace('cover-', '')

    categories = Category.objects.all()
    has_survey = SurveyResponse.objects.filter(student=profile).exists()

    return render(request, 'library/member_dashboard.html', {
        'stats': stats,
        'loans': loans,
        'history': history,
        'recommendations': ai_recommendations,
        'categories': categories,
        'has_survey': has_survey,
        'active_page': 'member',
    })

@login_required
def staff_dashboard_view(request):
    """
    Dedicated Librarian / Staff Workspace.
    Features: Circulation KPIs, Rule-Based Demand Analytics, Stock Shortage Alerts.
    """
    if not is_staff_or_librarian(request.user):
        messages.error(request, "Access Denied: Librarian privileges required.")
        return redirect('member_dashboard')

    total_copies = BookCopy.objects.exclude(status='archived').count()
    available_copies = BookCopy.objects.filter(status='available').count()
    active_loans = Loan.objects.filter(returned_at__isnull=True).select_related('member', 'copy__book')
    
    # Overdue loans
    today = timezone.localdate()
    overdue_loans = []
    for l in active_loans:
        if l.is_overdue:
            l.fine_amount = l.calculate_current_fine()
            overdue_loans.append(l)

    available_percent = int((available_copies / total_copies * 100)) if total_copies > 0 else 0

    stats = {
        'total_copies': f"{total_copies:,}",
        'available_copies': f"{available_copies:,}",
        'active_loans': f"{active_loans.count():,}",
        'overdue_loans': len(overdue_loans),
        'available_percent': available_percent,
    }

    # Circulation 7-day activity chart
    chart_data = []
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_issued = Loan.objects.filter(issue_date=day_date).count()
        day_returned = Loan.objects.filter(returned_at__date=day_date).count()
        chart_data.append({
            'label': day_date.strftime('%a'),
            'issued_height': min(100, max(15, int(day_issued * 20))),
            'returned_height': min(100, max(12, int(day_returned * 20))),
            'day_issued': day_issued,
            'day_returned': day_returned
        })

    # AI Overdue risk analysis
    ai_risk = get_overdue_risk_analysis()

    # Rule-Based Book Demand Analytics & Stock Shortage Alerts
    demand_data = get_book_demand_analytics()

    return render(request, 'library/staff_dashboard.html', {
        'stats': stats,
        'overdue_loans': overdue_loans[:8],
        'chart_data': chart_data,
        'ai_risk': ai_risk,
        'demand_data': demand_data,
        'active_page': 'staff',
    })

@login_required
def admin_portal_view(request):
    """
    Dedicated Administrator Security & Management Control Center.
    Protected strictly for System Administrators.
    """
    if not is_admin_user(request.user):
        messages.error(request, "Access Denied: Administrator security clearance required.")
        return redirect('dashboard_redirect')

    library_settings = LibrarySettings.get_settings()

    # 1. Action: Admin resets user password
    if request.method == 'POST' and request.POST.get('action') == 'reset_password':
        user_id = request.POST.get('target_user_id')
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if len(new_password) < 4:
            messages.error(request, "Password must be at least 4 characters long.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter.")
        else:
            target_user = get_object_or_404(User, pk=user_id)
            target_user.set_password(new_password)
            target_user.save()
            log_security_event(
                request,
                'PASSWORD_RESET',
                f"Admin '{request.user.username}' reset password for account '{target_user.username}'",
                user=request.user
            )
            messages.success(request, f"Password successfully reset for '{target_user.username}'!")
        return redirect('admin_portal')

    # 2. Action: Admin updates user role or status
    if request.method == 'POST' and request.POST.get('action') == 'update_user_role':
        profile_id = request.POST.get('profile_id')
        new_role = request.POST.get('role')
        new_status = request.POST.get('status')

        profile = get_object_or_404(MemberProfile, pk=profile_id)
        old_role = profile.role
        profile.role = new_role
        profile.status = new_status
        profile.save()

        if profile.user:
            profile.user.is_staff = (new_role in ['librarian', 'admin'])
            profile.user.is_superuser = (new_role == 'admin')
            profile.user.is_active = (new_status == 'active')
            profile.user.save()

        log_security_event(
            request,
            'ROLE_CHANGE',
            f"Admin updated user '{profile.name}' from {old_role} to {new_role} ({new_status})",
            user=request.user
        )
        messages.success(request, f"Updated role & status for {profile.name} ({profile.member_code}).")
        return redirect('admin_portal')

    # 3. Action: Admin updates system settings & demand weights
    if request.method == 'POST' and request.POST.get('action') == 'update_settings':
        try:
            library_settings.loan_period_days = int(request.POST.get('loan_period_days', 14))
            library_settings.max_active_loans = int(request.POST.get('max_active_loans', 3))
            library_settings.fine_per_day = Decimal(request.POST.get('fine_per_day', '5.00'))
            library_settings.weight_borrowing = Decimal(request.POST.get('weight_borrowing', '0.40'))
            library_settings.weight_reservation = Decimal(request.POST.get('weight_reservation', '0.25'))
            library_settings.weight_survey = Decimal(request.POST.get('weight_survey', '0.20'))
            library_settings.weight_search = Decimal(request.POST.get('weight_search', '0.15'))
            library_settings.shortage_threshold_demand = Decimal(request.POST.get('shortage_threshold_demand', '50.00'))
            library_settings.save()

            log_security_event(
                request,
                'SETTINGS_UPDATE',
                f"Circulation rules & demand formula weights updated (Loan={library_settings.loan_period_days}d, Fine={library_settings.fine_per_day} BDT)",
                user=request.user
            )
            messages.success(request, "Library circulation policies & demand weights updated successfully!")
        except Exception as e:
            messages.error(request, f"Failed to update settings: {e}")
        return redirect('admin_portal')

    # Database Statistics
    db_path = settings.DATABASES['default']['NAME']
    db_size_kb = 0
    db_modified = "N/A"
    if os.path.exists(db_path):
        db_size_kb = round(os.path.getsize(db_path) / 1024, 1)
        db_modified = timezone.datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S')

    db_stats = {
        'engine': 'SQLite 3 (Relational)',
        'path': os.path.basename(str(db_path)),
        'size_kb': db_size_kb,
        'last_modified': db_modified,
        'status': 'Online & Healthy',
        'total_users': User.objects.count(),
        'total_books': Book.objects.count(),
        'total_copies': BookCopy.objects.count(),
        'total_loans': Loan.objects.count(),
        'total_reservations': Reservation.objects.count(),
        'total_surveys': SurveyResponse.objects.count(),
        'total_security_logs': SecurityAuditLog.objects.count(),
    }

    users_list = User.objects.select_related('member_profile').order_by('username')
    security_logs = SecurityAuditLog.objects.select_related('user').order_by('-timestamp')[:30]

    return render(request, 'library/admin_portal.html', {
        'library_settings': library_settings,
        'db_stats': db_stats,
        'users_list': users_list,
        'security_logs': security_logs,
        'active_page': 'admin',
    })

@login_required
def admin_download_db_backup(request):
    """
    Allows Admin to download a timestamped snapshot of the live SQLite database.
    """
    if not is_admin_user(request.user):
        messages.error(request, "Access Denied: Only administrators can download database backups.")
        return redirect('dashboard_redirect')

    db_path = settings.DATABASES['default']['NAME']
    if not os.path.exists(db_path):
        raise Http404("Database file not found.")

    log_security_event(
        request,
        'DB_BACKUP',
        f"Admin '{request.user.username}' initiated and downloaded a database backup",
        user=request.user
    )

    today_str = timezone.localdate().strftime('%Y-%m-%d')
    filename = f"SLMS_Database_Backup_{today_str}.sqlite3"

    response = FileResponse(open(db_path, 'rb'), content_type='application/x-sqlite3')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def reports_view(request):
    if not is_staff_or_librarian(request.user):
        messages.error(request, "Access restricted: Staff privileges required.")
        return redirect('member_dashboard')

    report_type = request.GET.get('report', 'inventory').strip()
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()

    total_titles = Book.objects.count()
    available_copies = BookCopy.objects.filter(status='available').count()
    active_loans_count = Loan.objects.filter(returned_at__isnull=True).count()
    
    today = timezone.localdate()
    overdue_count = Loan.objects.filter(returned_at__isnull=True, due_date__lt=today).count()

    stats = {
        'total_titles': total_titles,
        'available_copies': available_copies,
        'active_loans': active_loans_count,
        'overdue_loans': overdue_count,
    }

    report_rows = []
    report_title = "Inventory Overview"

    if report_type == 'inventory':
        report_title = "Book Inventory & Physical Copies"
        copies = BookCopy.objects.select_related('book', 'book__category').order_by('book__title')
        for c in copies:
            report_rows.append({
                'title': f"{c.book.title} ({c.copy_code})",
                'category': c.book.category.name if c.book.category else 'General',
                'activity': f"Condition: {c.get_condition_display()}",
                'date': c.added_date,
                'status': c.get_status_display(),
                'is_overdue': False
            })

    elif report_type == 'loans':
        report_title = "Active Circulation Loans"
        loans = Loan.objects.filter(returned_at__isnull=True).select_related('copy__book', 'member').order_by('-issue_date')
        if date_from:
            loans = loans.filter(issue_date__gte=date_from)
        if date_to:
            loans = loans.filter(issue_date__lte=date_to)
        for l in loans:
            report_rows.append({
                'title': f"{l.copy.book.title} -> {l.member.name}",
                'category': l.member.member_code,
                'activity': f"Due: {l.due_date.strftime('%b %d')}",
                'date': l.issue_date,
                'status': 'Overdue' if l.is_overdue else 'Active Loan',
                'is_overdue': l.is_overdue
            })

    elif report_type == 'overdue':
        report_title = "Overdue Loans & Accumulated Fines"
        loans = Loan.objects.filter(returned_at__isnull=True, due_date__lt=today).select_related('copy__book', 'member')
        for l in loans:
            fine = l.calculate_current_fine()
            report_rows.append({
                'title': f"{l.copy.book.title} ({l.copy.copy_code})",
                'category': f"{l.member.name} ({l.member.member_code})",
                'activity': f"{l.overdue_days} days late (Fine: ৳{fine})",
                'date': l.due_date,
                'status': 'Critical Overdue',
                'is_overdue': True
            })

    elif report_type == 'members':
        report_title = "Library Members Directory"
        members = MemberProfile.objects.all().order_by('name')
        for m in members:
            report_rows.append({
                'title': m.name,
                'category': m.member_code,
                'activity': f"{m.department} · {m.loans.filter(returned_at__isnull=True).count()} active loan(s)",
                'date': m.joined_date,
                'status': m.get_status_display(),
                'is_overdue': m.status != 'active'
            })

    return render(request, 'library/reports.html', {
        'stats': stats,
        'report_title': report_title,
        'report_rows': report_rows,
        'report_updated': timezone.now(),
        'active_page': 'staff',
    })

@login_required
def report_csv_view(request):
    if not is_staff_or_librarian(request.user):
        messages.error(request, "Access restricted.")
        return redirect('member_dashboard')

    report_type = request.GET.get('report', 'inventory').strip()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="SLMS_{report_type}_report.csv"'

    writer = csv.writer(response)

    if report_type == 'inventory':
        writer.writerow(['Book Title', 'Copy Code', 'ISBN', 'Category', 'Shelf Location', 'Status', 'Condition'])
        for c in BookCopy.objects.select_related('book', 'book__category').all():
            writer.writerow([
                c.book.title,
                c.copy_code,
                c.book.isbn,
                c.book.category.name if c.book.category else 'General',
                c.book.shelf_location,
                c.get_status_display(),
                c.get_condition_display()
            ])

    elif report_type == 'overdue':
        today = timezone.localdate()
        writer.writerow(['Member Name', 'Member Code', 'Book Title', 'Copy Code', 'Issue Date', 'Due Date', 'Overdue Days', 'Fine Amount (BDT)'])
        for l in Loan.objects.filter(returned_at__isnull=True, due_date__lt=today).select_related('member', 'copy__book'):
            writer.writerow([
                l.member.name,
                l.member.member_code,
                l.copy.book.title,
                l.copy.copy_code,
                l.issue_date,
                l.due_date,
                l.overdue_days,
                l.calculate_current_fine()
            ])

    else:
        writer.writerow(['Member Name', 'Book Title', 'Copy Code', 'Issue Date', 'Due Date', 'Returned Date', 'Status', 'Fine (BDT)'])
        for l in Loan.objects.select_related('member', 'copy__book').all().order_by('-id')[:200]:
            writer.writerow([
                l.member.name,
                l.copy.book.title,
                l.copy.copy_code,
                l.issue_date,
                l.due_date,
                l.returned_at or 'Not Returned',
                'Returned' if l.is_returned else ('Overdue' if l.is_overdue else 'Active'),
                l.fine_amount
            ])

    return response
