from catalog.models import Book, Category
from circulation.models import Loan
from django.db.models import Count

def get_smart_recommendations(member_profile=None, limit=4):
    """
    Returns personalized book recommendations if a member_profile is provided.
    Falls back to trending and featured books if history is sparse.
    """
    if not member_profile:
        # Generic recommendation: top featured and most popular books
        return Book.objects.filter(is_featured=True)[:limit]

    # 1. Categories previously borrowed by this student
    borrowed_categories = Loan.objects.filter(
        member=member_profile
    ).values_list('copy__book__category', flat=True).distinct()

    # 2. Books already borrowed by this student
    already_borrowed_book_ids = Loan.objects.filter(
        member=member_profile
    ).values_list('copy__book_id', flat=True).distinct()

    recommended = []

    if borrowed_categories:
        # Find books in preferred categories not yet borrowed
        cat_recs = Book.objects.filter(
            category__in=borrowed_categories
        ).exclude(
            id__in=already_borrowed_book_ids
        ).distinct()[:limit]
        recommended.extend(list(cat_recs))

    # If still need more, fill with featured / popular books
    if len(recommended) < limit:
        needed = limit - len(recommended)
        fallback = Book.objects.exclude(
            id__in=[b.id for b in recommended] + list(already_borrowed_book_ids)
        ).order_by('-is_featured', '?')[:needed]
        recommended.extend(list(fallback))

    return recommended[:limit]

def get_popular_books(limit=4):
    """
    Returns the most frequently borrowed books across all members.
    """
    popular = Book.objects.annotate(
        borrow_count=Count('copies__loans')
    ).order_by('-borrow_count', '-is_featured')[:limit]
    
    if not popular.exists():
        return Book.objects.all()[:limit]
    return popular
