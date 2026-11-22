import re
from catalog.models import Book, Category, BookCopy
from circulation.models import LibrarySettings
from smart_ai.models import SmartQueryLog

def process_smart_assistant_query(query_text, user=None):
    """
    Intelligent AI assistant processor.
    Answers natural language queries about books, availability, rules, and recommendations.
    """
    query = (query_text or "").strip().lower()
    if not query:
        return {
            'reply': "Hello! I am **LibroAI**, your Smart Library Assistant. How can I assist you with book searches, availability, or circulation policies today?",
            'suggestions': [],
            'quick_chips': ["Search Python books", "What is the fine rate?", "Show available books", "Library rules"]
        }

    settings = LibrarySettings.get_settings()
    reply = ""
    book_suggestions = []
    quick_chips = ["Explore Catalog", "My Borrowed Books", "Contact Librarian"]

    # 1. Rule & Policy Queries
    if any(k in query for k in ["fine", "penalty", "charge", "late fee", "jôrimana"]):
        reply = (
            f"💰 **Overdue Fine Policy:**\n\n"
            f"• Our standard daily overdue fine rate is **{settings.fine_per_day} BDT** per day.\n"
            f"• Fines are calculated automatically upon returning the book if it passes the due date.\n"
            f"• You can check any accumulated fines directly from your **Student Dashboard**."
        )
        quick_chips = ["Check Loan Period", "View My Dashboard", "Search Books"]

    elif any(k in query for k in ["duration", "how many days", "loan period", "due date", "limit", "rules"]):
        reply = (
            f"📖 **Library Borrowing Rules:**\n\n"
            f"• **Loan Period:** You can borrow books for up to **{settings.loan_period_days} days**.\n"
            f"• **Max Books:** A student can hold at most **{settings.max_active_loans} active book loans** simultaneously.\n"
            f"• **Renewal:** Each loan can be renewed up to **{settings.renewal_limit} time(s)** before the due date if there are no pending reservations."
        )
        quick_chips = ["Search Books", "What is the fine rate?", "My Loans"]

    # 2. Recommendation Requests
    elif any(k in query for k in ["recommend", "suggest", "popular", "best book", "top"]):
        featured_books = Book.objects.filter(is_featured=True)[:4]
        if not featured_books:
            featured_books = Book.objects.all()[:4]
        
        reply = "✨ **Here are our top recommended picks from the library collection:**"
        for b in featured_books:
            book_suggestions.append({
                'id': b.id,
                'title': b.title,
                'author': b.author,
                'category': b.category.name if b.category else 'General',
                'available': b.is_available,
                'available_count': b.available_copies_count,
                'url': f"/books/{b.id}/"
            })
        quick_chips = ["Software Engineering", "Algorithms", "AI & ML"]

    # 3. Specific Subject / Category Searches
    else:
        # Check if query matches a category
        matching_cats = Category.objects.filter(name__icontains=query)
        if matching_cats.exists():
            cat = matching_cats.first()
            books = Book.objects.filter(category=cat)[:4]
            reply = f"📚 Found books under the **{cat.name}** category:"
            for b in books:
                book_suggestions.append({
                    'id': b.id,
                    'title': b.title,
                    'author': b.author,
                    'category': cat.name,
                    'available': b.is_available,
                    'available_count': b.available_copies_count,
                    'url': f"/books/{b.id}/"
                })
        else:
            # Search by title, author, or keyword
            keywords = [w for w in re.split(r'\s+', query) if len(w) > 2 and w not in ['book', 'books', 'have', 'find', 'show', 'search', 'want']]
            if keywords:
                search_word = keywords[0]
                matched_books = Book.objects.filter(
                    title__icontains=search_word
                ) | Book.objects.filter(
                    author__icontains=search_word
                ) | Book.objects.filter(
                    description__icontains=search_word
                )
                matched_books = matched_books.distinct()[:4]
            else:
                matched_books = Book.objects.all()[:3]

            if matched_books.exists():
                reply = f"🔍 Found {matched_books.count()} matching title(s) for your inquiry:"
                for b in matched_books:
                    book_suggestions.append({
                        'id': b.id,
                        'title': b.title,
                        'author': b.author,
                        'category': b.category.name if b.category else 'General',
                        'available': b.is_available,
                        'available_count': b.available_copies_count,
                        'url': f"/books/{b.id}/"
                    })
            else:
                reply = f"I couldn't find an exact match for '{query_text}'. Would you like to browse our full catalogue or search by another keyword?"
                quick_chips = ["Browse All Books", "Computer Science", "Algorithms"]

    # Log query
    try:
        SmartQueryLog.objects.create(
            user=user if user and user.is_authenticated else None,
            query_text=query_text[:300],
            response_text=reply[:500]
        )
    except Exception:
        pass

    return {
        'reply': reply,
        'books': book_suggestions,
        'quick_chips': quick_chips
    }
