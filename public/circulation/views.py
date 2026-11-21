from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from circulation.models import Loan, BookCopy, MemberProfile, LibrarySettings
from accounts.views import is_staff_or_librarian

@login_required
@user_passes_test(is_staff_or_librarian)
def circulation_view(request):
    settings = LibrarySettings.get_settings()
    active_members = MemberProfile.objects.filter(status='active').order_by('name')
    available_copies = BookCopy.objects.filter(status='available').select_related('book').order_by('book__title')
    active_loans = Loan.objects.filter(returned_at__isnull=True).select_related('member', 'copy__book').order_by('-issue_date')
    recent_loans = Loan.objects.all().select_related('member', 'copy__book').order_by('-id')[:12]

    # Precalculate helpers for template
    for l in recent_loans:
        l.is_overdue_flag = l.is_overdue
        l.status_label = 'Overdue' if l.is_overdue else ('Returned' if l.is_returned else 'On loan')

    return render(request, 'library/circulation.html', {
        'active_members': active_members,
        'available_copies': available_copies,
        'active_loans': active_loans,
        'recent_loans': recent_loans,
        'settings': settings,
        'active_page': 'staff',
    })

@login_required
@user_passes_test(is_staff_or_librarian)
def issue_book_view(request):
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        copy_id = request.POST.get('copy_id')

        if not member_id or not copy_id:
            messages.error(request, "Please select both a member and a book copy.")
            return redirect('circulation')

        member = get_object_or_404(MemberProfile, pk=member_id)
        copy = get_object_or_404(BookCopy, pk=copy_id)
        settings = LibrarySettings.get_settings()

        # Validation 1: Member eligibility check
        eligible, reason = member.can_borrow(settings.max_active_loans)
        if not eligible:
            messages.error(request, f"Issue denied: {reason}")
            return redirect('circulation')

        # Validation 2: Copy availability check
        if copy.status != 'available':
            messages.error(request, f"Issue denied: Copy '{copy.copy_code}' is currently {copy.get_status_display()}.")
            return redirect('circulation')

        # Validation 3: Duplicate active loan check
        if Loan.objects.filter(copy=copy, returned_at__isnull=True).exists():
            messages.error(request, f"Issue denied: Copy '{copy.copy_code}' already has an active loan.")
            return redirect('circulation')

        # Proceed with Issue
        loan = Loan.objects.create(
            copy=copy,
            member=member,
            issued_by=request.user,
            issue_date=timezone.localdate(),
            notes="Issued via circulation desk"
        )
        copy.status = 'issued'
        copy.save()

        messages.success(request, f"Book '{copy.book.title}' (Copy {copy.copy_code}) issued to {member.name}. Due on {loan.due_date.strftime('%b %d, %Y')}.")
        return redirect('circulation')

    return redirect('circulation')

@login_required
@user_passes_test(is_staff_or_librarian)
def return_book_view(request):
    if request.method == 'POST':
        loan_id = request.POST.get('loan_id')
        if not loan_id:
            messages.error(request, "Please select an active loan to return.")
            return redirect('circulation')

        loan = get_object_or_404(Loan, pk=loan_id)
        if loan.is_returned:
            messages.warning(request, f"This book was already returned on {loan.returned_at.strftime('%b %d, %Y')}.")
            return redirect('circulation')

        loan.return_book()

        if loan.fine_amount > 0:
            messages.warning(
                request,
                f"Book returned! It was {loan.overdue_days} day(s) overdue. Calculated fine: ৳ {loan.fine_amount} BDT."
            )
        else:
            messages.success(request, f"Book '{loan.copy.book.title}' successfully returned on time! Copy status updated to Available.")

        return redirect('circulation')

    return redirect('circulation')

@login_required
def renew_book_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    
    # Check permission: only the member who owns the loan or a librarian can renew
    is_owner = hasattr(request.user, 'member_profile') and request.user.member_profile == loan.member
    if not (is_owner or is_staff_or_librarian(request.user)):
        messages.error(request, "You do not have permission to renew this loan.")
        return redirect('member_dashboard')

    success, msg = loan.renew_loan()
    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    if is_staff_or_librarian(request.user):
        return redirect('circulation')
    return redirect('member_dashboard')
