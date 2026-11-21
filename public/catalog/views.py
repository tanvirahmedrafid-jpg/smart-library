from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from catalog.models import Book, BookCopy, Category
from catalog.forms import BookForm
from accounts.models import MemberProfile
from circulation.models import Loan
from accounts.views import is_staff_or_librarian
from smart_ai.models import SearchLog

def home_view(request):
    total_titles = Book.objects.count()
    available_copies = BookCopy.objects.filter(status='available').count()
    active_members = MemberProfile.objects.filter(status='active').count()

    stats = {
        'total_titles': "128,436",
        'available_copies': "96,712",
        'active_members': "24,859",
        'opening_hours': "8:00 AM – 8:00 PM",
        'live_titles': f"{total_titles:,}",
        'live_available': f"{available_copies:,}",
    }

    # Order mockup books first if they exist
    preferred_titles = [
        'Introduction to Algorithms',
        'Database System Concepts',
        'English Literature: A Survey',
        'Fundamentals of Physics'
    ]
    featured_books = []
    for title in preferred_titles:
        b = Book.objects.filter(title__icontains=title).first()
        if b and b not in featured_books:
            featured_books.append(b)

    # Append any remaining featured books
    for b in Book.objects.filter(is_featured=True):
        if b not in featured_books:
            featured_books.append(b)

    for b in featured_books:
        b.cover_style = b.cover_theme.replace('cover-', '')

    # Browse Categories
    category_slugs = ['cs', 'business', 'literature', 'science']
    categories = []
    for slug in category_slugs:
        cat = Category.objects.filter(slug=slug).first()
        if cat:
            categories.append(cat)
    if not categories:
        categories = list(Category.objects.all()[:4])

    # User active loans info if logged in
    user_loans_count = 0
    if request.user.is_authenticated:
        profile = getattr(request.user, 'member_profile', None)
        if profile:
            user_loans_count = Loan.objects.filter(member=profile, status='issued').count()

    return render(request, 'library/home.html', {
        'stats': stats,
        'featured_books': featured_books[:4],
        'more_featured_books': featured_books[4:8],
        'categories': categories,
        'user_loans_count': user_loans_count,
        'active_page': 'home',
    })

def catalog_view(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    available_only = request.GET.get('available', '').strip()
    sort_by = request.GET.get('sort', 'title').strip()

    books_qs = Book.objects.all()

    if query:
        books_qs = books_qs.filter(
            title__icontains=query
        ) | books_qs.filter(
            author__icontains=query
        ) | books_qs.filter(
            isbn__icontains=query
        )
        # Log search for demand analytics (Q indicator)
        try:
            SearchLog.objects.create(
                query=query[:250],
                matched_book=books_qs.first(),
                user=request.user if request.user.is_authenticated else None
            )
        except Exception:
            pass

    if category_id:
        books_qs = books_qs.filter(category_id=category_id)

    if available_only == '1':
        books_qs = books_qs.filter(copies__status='available').distinct()

    if sort_by == 'newest':
        books_qs = books_qs.order_by('-created_at')
    else:
        books_qs = books_qs.order_by('title')

    # Assign helper attributes for cards
    categories = Category.objects.all()
    paginator = Paginator(books_qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for b in page_obj:
        b.cover_style = b.cover_theme.replace('cover-', '')

    return render(request, 'library/catalog.html', {
        'books': page_obj,
        'categories': categories,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'active_page': 'catalog',
    })

def book_detail_view(request, pk):
    book = get_object_or_404(Book, pk=pk)
    book.cover_style = book.cover_theme.replace('cover-', '')
    
    physical_copies = book.copies.all()
    related_books = Book.objects.filter(category=book.category).exclude(id=book.id)[:4]

    return render(request, 'library/book_detail.html', {
        'book': book,
        'physical_copies': physical_copies,
        'related_books': related_books,
        'active_page': 'catalog',
    })

@login_required
@user_passes_test(is_staff_or_librarian)
def books_manage_view(request):
    query = request.GET.get('q', '').strip()
    books_qs = Book.objects.all().order_by('-created_at')
    if query:
        books_qs = books_qs.filter(
            title__icontains=query
        ) | books_qs.filter(
            author__icontains=query
        ) | books_qs.filter(
            isbn__icontains=query
        )
        # Log search for demand analytics (Q indicator)
        try:
            SearchLog.objects.create(
                query=query[:250],
                matched_book=books_qs.first(),
                user=request.user if request.user.is_authenticated else None
            )
        except Exception:
            pass

    for b in books_qs:
        b.cover_style = b.cover_theme.replace('cover-', '')

    book_form = BookForm()
    paginator = Paginator(books_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'library/books.html', {
        'books': page_obj,
        'page_obj': page_obj,
        'book_form': book_form,
        'categories': categories,
        'active_page': 'staff',
    })

@login_required
@user_passes_test(is_staff_or_librarian)
def book_create_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            initial_copies = form.cleaned_data.get('initial_copies') or 1
            # Automatically create copies
            for i in range(1, initial_copies + 1):
                cat_prefix = book.category.slug[:4].upper() if book.category else 'GEN'
                BookCopy.objects.create(
                    book=book,
                    copy_code=f"SLM-{cat_prefix}-{book.id:03d}-C{i}",
                    status='available',
                    condition='new'
                )
            messages.success(request, f"Book '{book.title}' created with {initial_copies} copy/copies!")
            return redirect('books')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = BookForm()

    return render(request, 'library/books.html', {
        'books': Book.objects.all()[:10],
        'book_form': form,
        'categories': Category.objects.all(),
        'active_page': 'staff',
    })

@login_required
@user_passes_test(is_staff_or_librarian)
def book_edit_view(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated book '{book.title}'.")
            return redirect('books')
        else:
            messages.error(request, "Please check the errors.")
    else:
        form = BookForm(instance=book)

    return render(request, 'library/books.html', {
        'books': Book.objects.all()[:10],
        'book': book,
        'book_form': form,
        'categories': Category.objects.all(),
        'active_page': 'staff',
    })

# ========================================================
# Librarian AI Command Assistant API Endpoints
# ========================================================
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from library.services.librarian_ai import interpret_librarian_command, execute_librarian_command
from accounts.models import log_security_event

@login_required
@user_passes_test(is_staff_or_librarian)
@require_http_methods(["POST"])
def librarian_interpret_command_api(request):
    """
    Interprets natural language librarian commands using Gemini / Local NLP.
    Returns preview of extracted fields and checks for ISBN duplicates.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        command = data.get('command', '').strip()
    except Exception:
        command = request.POST.get('command', '').strip()

    result = interpret_librarian_command(command)
    return JsonResponse(result)

@login_required
@user_passes_test(is_staff_or_librarian)
@require_http_methods(["POST"])
def librarian_execute_command_api(request):
    """
    Executes a confirmed librarian command after review.
    Saves Book and physical BookCopy barcode instances.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST.dict()

    result = execute_librarian_command(request.user, data)
    if result.get('success'):
        log_security_event(
            request,
            'AI_COMMAND_EXECUTE',
            f"Librarian '{request.user.username}' executed action: {result.get('action_executed')} on '{result.get('book_title')}'",
            user=request.user
        )
    return JsonResponse(result)

