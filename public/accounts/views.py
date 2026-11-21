from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from accounts.models import MemberProfile, SecurityAuditLog, log_security_event
from accounts.forms import MemberForm

def is_staff_or_librarian(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    profile = getattr(user, 'member_profile', None)
    return bool(profile and profile.is_librarian)

def is_admin_user(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'member_profile', None)
    return bool(profile and (profile.role == 'admin' or profile.is_admin))

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_security_event(request, 'LOGIN_SUCCESS', f"User '{user.username}' logged in successfully", user=user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard_redirect')
        else:
            failed_name = request.POST.get('username', 'Unknown')
            log_security_event(request, 'LOGIN_FAILED', f"Failed login attempt for username '{failed_name}'")
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'library/login.html', {'form': form, 'active_page': 'login'})

def logout_view(request):
    username = request.user.username if request.user.is_authenticated else None
    if request.user.is_authenticated:
        log_security_event(request, 'LOGOUT', f"User '{username}' logged out successfully", user=request.user)
    logout(request)
    messages.success(request, "You have been successfully logged out of S-liBro.")
    return redirect('login')

@login_required
def dashboard_redirect(request):
    if is_admin_user(request.user):
        return redirect('admin_portal')
    elif is_staff_or_librarian(request.user):
        return redirect('staff_dashboard')
    return redirect('member_dashboard')

@login_required
def members_view(request):
    if not is_staff_or_librarian(request.user):
        messages.error(request, "Access restricted: Staff privileges required.")
        return redirect('dashboard_redirect')

    query = request.GET.get('q', '').strip()
    members_qs = MemberProfile.objects.all().order_by('-joined_date', 'name')
    if query:
        members_qs = members_qs.filter(
            name__icontains=query
        ) | members_qs.filter(
            member_code__icontains=query
        ) | members_qs.filter(
            email__icontains=query
        )

    if request.method == 'POST':
        member_form = MemberForm(request.POST)
        if member_form.is_valid():
            new_member = member_form.save()
            log_security_event(request, 'STATUS_CHANGE', f"New member '{new_member.name}' registered with role {new_member.role}", user=request.user)
            messages.success(request, "Member profile registered successfully!")
            return redirect('members')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        member_form = MemberForm()

    paginator = Paginator(members_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'library/members.html', {
        'members': page_obj,
        'page_obj': page_obj,
        'member_form': member_form,
        'active_page': 'staff',
    })

@login_required
def member_edit_view(request, pk):
    if not is_staff_or_librarian(request.user):
        messages.error(request, "Access restricted: Staff privileges required.")
        return redirect('dashboard_redirect')

    member = get_object_or_404(MemberProfile, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            log_security_event(request, 'STATUS_CHANGE', f"Updated member '{member.name}' profile and status ({member.status})", user=request.user)
            messages.success(request, f"Updated profile for {member.name}.")
            return redirect('members')
        else:
            messages.error(request, "Please check the form fields.")
    else:
        form = MemberForm(instance=member)

    return render(request, 'library/members.html', {
        'members': MemberProfile.objects.all()[:10],
        'member_form': form,
        'editing_member': member,
        'active_page': 'staff',
    })
