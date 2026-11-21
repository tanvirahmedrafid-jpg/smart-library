from django.utils import timezone
from circulation.models import Loan, Reservation, LibrarySettings
from catalog.models import Book, BookCopy, Category
from smart_ai.models import SurveyResponse, SearchLog
from decimal import Decimal
from django.db.models import Count, Q

def get_overdue_risk_analysis():
    """
    Analyzes all active loans and calculates risk status,
    predicted fines, and upcoming due items for librarians.
    """
    settings = LibrarySettings.get_settings()
    today = timezone.localdate()
    active_loans = Loan.objects.filter(returned_at__isnull=True).select_related('copy__book', 'member')

    overdue_loans = []
    approaching_loans = []
    normal_loans = []

    total_projected_fine = Decimal('0.00')

    for loan in active_loans:
        days_diff = (loan.due_date - today).days
        if days_diff < 0:
            # Overdue
            overdue_days = abs(days_diff)
            estimated_fine = Decimal(overdue_days) * settings.fine_per_day
            total_projected_fine += estimated_fine
            overdue_loans.append({
                'loan': loan,
                'status': 'Overdue',
                'risk_level': 'high',
                'days_overdue': overdue_days,
                'fine': estimated_fine,
                'badge_class': 'pill-overdue'
            })
        elif days_diff <= 2:
            # Approaching due in 48 hours
            approaching_loans.append({
                'loan': loan,
                'status': f'Due in {days_diff}d' if days_diff > 0 else 'Due Today',
                'risk_level': 'medium',
                'days_left': days_diff,
                'fine': Decimal('0.00'),
                'badge_class': 'pill-warning'
            })
        else:
            normal_loans.append({
                'loan': loan,
                'status': f'{days_diff} days left',
                'risk_level': 'low',
                'days_left': days_diff,
                'fine': Decimal('0.00'),
                'badge_class': 'pill-active'
            })

    return {
        'total_active': active_loans.count(),
        'overdue_count': len(overdue_loans),
        'approaching_count': len(approaching_loans),
        'normal_count': len(normal_loans),
        'total_projected_fine': total_projected_fine,
        'overdue_loans': overdue_loans,
        'approaching_loans': approaching_loans,
    }


def get_book_demand_analytics():
    """
    Implements Rule-Based Book Demand Analytics & Stock Shortage Detection.
    Formula: D = wB*B + wR*R + wS*S + wQ*Q
    Normalized on a 0-100 scale.
    """
    settings = LibrarySettings.get_settings()
    w_B = float(settings.weight_borrowing)
    w_R = float(settings.weight_reservation)
    w_S = float(settings.weight_survey)
    w_Q = float(settings.weight_search)
    threshold = float(settings.shortage_threshold_demand)

    books = Book.objects.select_related('category').prefetch_related('copies', 'reservations')

    raw_data = []
    max_b = 1
    max_r = 1
    max_s = 1
    max_q = 1

    for book in books:
        # 1. Borrowing Activity (B): Total historical loans
        b_count = Loan.objects.filter(copy__book=book).count()

        # 2. Reservation Activity (R): Total reservation queue
        r_count = Reservation.objects.filter(book=book).count()

        # 3. Survey Interest (S): Student survey interest in category or suggested title
        s_count = 0
        if book.category:
            s_count += SurveyResponse.objects.filter(preferred_category=book.category).count()
        s_count += SurveyResponse.objects.filter(suggested_title__icontains=book.title[:20]).count()

        # 4. Search Activity (Q): Searches recorded for this title
        q_count = SearchLog.objects.filter(
            Q(matched_book=book) | Q(query__icontains=book.title[:15])
        ).count()

        max_b = max(max_b, b_count)
        max_r = max(max_r, r_count)
        max_s = max(max_s, s_count)
        max_q = max(max_q, q_count)

        raw_data.append({
            'book': book,
            'b_raw': b_count,
            'r_raw': r_count,
            's_raw': s_count,
            'q_raw': q_count,
            'available_copies': book.available_copies_count,
            'total_copies': book.total_copies_count,
        })

    # Normalize and calculate overall demand score D
    analytics_results = []
    shortage_alerts = []

    for item in raw_data:
        b_norm = (item['b_raw'] / max_b) * 100.0
        r_norm = (item['r_raw'] / max_r) * 100.0
        s_norm = (item['s_raw'] / max_s) * 100.0
        q_norm = (item['q_raw'] / max_q) * 100.0

        # Weighted composite score
        demand_score = (w_B * b_norm) + (w_R * r_norm) + (w_S * s_norm) + (w_Q * q_norm)
        demand_score = round(demand_score, 1)

        # Stock Shortage Rule: High demand score and 1 or 0 copies available
        is_shortage = False
        shortage_level = 'NORMAL'
        explanation = []

        if item['b_raw'] > 0:
            explanation.append(f"Borrowing ({item['b_raw']} loans)")
        if item['r_raw'] > 0:
            explanation.append(f"Reservations ({item['r_raw']} queued)")
        if item['s_raw'] > 0:
            explanation.append(f"Survey votes ({item['s_raw']})")
        if item['q_raw'] > 0:
            explanation.append(f"Searches ({item['q_raw']})")

        explanation_str = " + ".join(explanation) if explanation else "Base catalog interest"

        if demand_score >= threshold and item['available_copies'] <= 1:
            is_shortage = True
            shortage_level = 'CRITICAL' if item['available_copies'] == 0 else 'WARNING'
            shortage_alerts.append({
                'book': item['book'],
                'demand_score': demand_score,
                'shortage_level': shortage_level,
                'available_copies': item['available_copies'],
                'total_copies': item['total_copies'],
                'waiting_reservations': item['r_raw'],
                'explanation': f"High observed demand ({demand_score} pts) with only {item['available_copies']} copy available on shelf. Acquisition recommended."
            })

        analytics_results.append({
            'book': item['book'],
            'demand_score': demand_score,
            'b_raw': item['b_raw'],
            'b_norm': round(b_norm, 1),
            'r_raw': item['r_raw'],
            'r_norm': round(r_norm, 1),
            's_raw': item['s_raw'],
            's_norm': round(s_norm, 1),
            'q_raw': item['q_raw'],
            'q_norm': round(q_norm, 1),
            'available_copies': item['available_copies'],
            'total_copies': item['total_copies'],
            'is_shortage': is_shortage,
            'shortage_level': shortage_level,
            'explanation': explanation_str,
        })

    # Sort descending by demand score
    analytics_results.sort(key=lambda x: x['demand_score'], reverse=True)

    # Attach rank
    for rank, item in enumerate(analytics_results, 1):
        item['rank'] = rank

    top_demand_book = analytics_results[0] if analytics_results else None

    return {
        'rankings': analytics_results,
        'shortage_alerts': shortage_alerts,
        'shortage_count': len(shortage_alerts),
        'top_book': top_demand_book,
        'weights': {
            'w_B': int(w_B * 100),
            'w_R': int(w_R * 100),
            'w_S': int(w_S * 100),
            'w_Q': int(w_Q * 100),
        },
        'formula': f"D = {w_B}·B + {w_R}·R + {w_S}·S + {w_Q}·Q",
        'threshold': threshold,
    }
