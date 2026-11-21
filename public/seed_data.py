import os
import django
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_library.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import MemberProfile, SecurityAuditLog
from catalog.models import Category, Book, BookCopy
from circulation.models import LibrarySettings, Loan, Reservation
from smart_ai.models import SurveyResponse, SearchLog

def seed_database():
    print("[*] Seeding Smart Library Management System database...")

    # 1. Ensure Library Settings with Demand Weights
    settings = LibrarySettings.get_settings()
    settings.loan_period_days = 14
    settings.max_active_loans = 3
    settings.fine_per_day = Decimal('5.00')
    settings.renewal_limit = 1
    settings.weight_borrowing = Decimal('0.40')
    settings.weight_reservation = Decimal('0.25')
    settings.weight_survey = Decimal('0.20')
    settings.weight_search = Decimal('0.15')
    settings.shortage_threshold_demand = Decimal('50.00')
    settings.save()
    print("[OK] Library Settings configured (14 days, max 3 books, 5 BDT/day, demand weights set)")

    # 2. Users & Member Profiles
    # Admin
    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@campus.library', 'first_name': 'System', 'last_name': 'Admin'})
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.set_password('admin123')
    admin_user.save()
    MemberProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'role': 'admin',
            'member_code': 'ADM-001',
            'name': 'System Administrator',
            'email': 'admin@campus.library',
            'phone': '01700000001',
            'department': 'Central Library'
        }
    )
    print("[OK] Admin user created: admin / admin123")

    # Librarian
    lib_user, _ = User.objects.get_or_create(username='librarian', defaults={'email': 'librarian@campus.library', 'first_name': 'Afroza', 'last_name': 'Begum'})
    lib_user.is_staff = True
    lib_user.set_password('lib123')
    lib_user.save()
    MemberProfile.objects.get_or_create(
        user=lib_user,
        defaults={
            'role': 'librarian',
            'member_code': 'LIB-001',
            'name': 'Afroza Begum (Chief Librarian)',
            'email': 'librarian@campus.library',
            'phone': '01700000002',
            'department': 'Central Library'
        }
    )
    print("[OK] Librarian user created: librarian / lib123")

    # Student 1: Tanvir Ahmmed
    stu1_user, _ = User.objects.get_or_create(username='tanvir', defaults={'email': 'tanvir@campus.library', 'first_name': 'Tanvir', 'last_name': 'Ahmmed'})
    stu1_user.set_password('stu123')
    stu1_user.save()
    stu1_profile, _ = MemberProfile.objects.get_or_create(
        user=stu1_user,
        defaults={
            'role': 'student',
            'member_code': 'STU-2024-001',
            'name': 'Tanvir Ahmmed',
            'email': 'tanvir@campus.library',
            'phone': '01711223344',
            'department': 'Computer Science',
            'status': 'active'
        }
    )
    print("[OK] Student user created: tanvir / stu123")

    # Student 2: Rahim Chowdhury
    stu2_user, _ = User.objects.get_or_create(username='rahim', defaults={'email': 'rahim@campus.library', 'first_name': 'Rahim', 'last_name': 'Chowdhury'})
    stu2_user.set_password('stu123')
    stu2_user.save()
    stu2_profile, _ = MemberProfile.objects.get_or_create(
        user=stu2_user,
        defaults={
            'role': 'student',
            'member_code': 'STU-2024-002',
            'name': 'Rahim Chowdhury',
            'email': 'rahim@campus.library',
            'phone': '01722334455',
            'department': 'Computer Science',
            'status': 'active'
        }
    )
    print("[OK] Student user created: rahim / stu123")

    # 3. Categories
    categories_data = [
        ("Software Engineering & Architecture", "se-arch", "bi-diagram-3", "Software construction, patterns, and system design"),
        ("Algorithms & Data Structures", "algo-ds", "bi-code-square", "Core algorithms, complexity, and problem solving"),
        ("Artificial Intelligence & ML", "ai-ml", "bi-cpu", "Machine learning, neural networks, and modern AI"),
        ("Database Systems & Cloud", "db-cloud", "bi-server", "Relational databases, distributed systems, and cloud architecture"),
        ("Operating Systems & Networks", "os-net", "bi-hdd-network", "Operating system kernels, concurrency, and computer networking"),
    ]

    cat_map = {}
    for name, slug, icon, desc in categories_data:
        cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'icon': icon, 'description': desc})
        cat_map[slug] = cat
    print("[OK] Categories created")

    # 4. Books and Physical Copies
    books_data = [
        {
            'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
            'author': 'Robert C. Martin',
            'isbn': '978-0132350884',
            'category': cat_map['se-arch'],
            'publisher': 'Prentice Hall',
            'edition': '1st Edition',
            'publication_year': 2008,
            'shelf_location': 'Rack SE-01, Shelf A',
            'description': 'Even bad code can function. But if code isn’t clean, it can bring a development organization to its knees. A timeless guide to writing readable, maintainable software.',
            'cover_theme': 'cover-orange',
            'is_featured': True,
            'copies_count': 3
        },
        {
            'title': 'Introduction to Algorithms (CLRS)',
            'author': 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein',
            'isbn': '978-0262033848',
            'category': cat_map['algo-ds'],
            'publisher': 'MIT Press',
            'edition': '3rd Edition',
            'publication_year': 2009,
            'shelf_location': 'Rack AL-02, Shelf B',
            'description': 'The definitive textbook on algorithms, covering data structures, graph theory, dynamic programming, and complexity with mathematical rigor.',
            'cover_theme': 'cover-blue',
            'is_featured': True,
            'copies_count': 4
        },
        {
            'title': 'Designing Data-Intensive Applications',
            'author': 'Martin Kleppmann',
            'isbn': '978-1449373320',
            'category': cat_map['db-cloud'],
            'publisher': "O'Reilly Media",
            'edition': '1st Edition',
            'publication_year': 2017,
            'shelf_location': 'Rack DB-04, Shelf C',
            'description': 'The definitive guide to navigating distributed databases, batch/stream processing, scalability, and high-reliability systems.',
            'cover_theme': 'cover-sand',
            'is_featured': True,
            'copies_count': 3
        },
        {
            'title': 'Artificial Intelligence: A Modern Approach',
            'author': 'Stuart Russell, Peter Norvig',
            'isbn': '978-0136042594',
            'category': cat_map['ai-ml'],
            'publisher': 'Pearson',
            'edition': '4th Global Edition',
            'publication_year': 2020,
            'shelf_location': 'Rack AI-01, Shelf A',
            'description': 'The leading textbook in AI, exploring intelligent agents, heuristic search, deep learning, NLP, and robotics.',
            'cover_theme': 'cover-purple',
            'is_featured': True,
            'copies_count': 3
        },
        {
            'title': 'Modern Operating Systems',
            'author': 'Andrew S. Tanenbaum, Herbert Bos',
            'isbn': '978-0133591620',
            'category': cat_map['os-net'],
            'publisher': 'Pearson',
            'edition': '4th Edition',
            'publication_year': 2014,
            'shelf_location': 'Rack OS-03, Shelf D',
            'description': 'Comprehensive coverage of OS fundamentals: processes, virtual memory, threads, file systems, virtualization, and multi-core security.',
            'cover_theme': 'cover-sage',
            'is_featured': False,
            'copies_count': 2
        },
        {
            'title': 'The Pragmatic Programmer: Your Journey To Mastery',
            'author': 'David Thomas, Andrew Hunt',
            'isbn': '978-0135957059',
            'category': cat_map['se-arch'],
            'publisher': 'Addison-Wesley',
            'edition': '20th Anniversary Edition',
            'publication_year': 2019,
            'shelf_location': 'Rack SE-02, Shelf C',
            'description': 'Practical philosophy and actionable wisdom for professional developers who want to write cleaner, more resilient code.',
            'cover_theme': 'cover-rose',
            'is_featured': True,
            'copies_count': 3
        },
        {
            'title': 'Python Crash Course: A Hands-On, Project-Based Introduction',
            'author': 'Eric Matthes',
            'isbn': '978-1593279288',
            'category': cat_map['se-arch'],
            'publisher': 'No Starch Press',
            'edition': '3rd Edition',
            'publication_year': 2023,
            'shelf_location': 'Rack PY-01, Shelf A',
            'description': 'A fast-paced, thorough introduction to Python programming, web development with Django, and data visualization.',
            'cover_theme': 'cover-blue',
            'is_featured': False,
            'copies_count': 3
        }
    ]

    all_copies = []
    for b_data in books_data:
        copies_count = b_data.pop('copies_count')
        book, _ = Book.objects.get_or_create(isbn=b_data['isbn'], defaults=b_data)
        
        # Create physical copies
        for c_idx in range(1, copies_count + 1):
            copy_code = f"SLM-{book.category.slug[:4].upper()}-{book.id:03d}-C{c_idx}"
            copy, _ = BookCopy.objects.get_or_create(
                copy_code=copy_code,
                defaults={'book': book, 'status': 'available', 'condition': 'good'}
            )
            all_copies.append(copy)
    print(f"[OK] Books and physical copies created (Total: {len(all_copies)} copies)")

    # 5. Circulation Transactions
    today = timezone.localdate()

    # Loan 1: Active safe loan for Tanvir (Clean Code, due in 10 days)
    clean_code_copy = BookCopy.objects.filter(book__title__icontains='Clean Code', status='available').first()
    if clean_code_copy and not Loan.objects.filter(copy=clean_code_copy, returned_at__isnull=True).exists():
        Loan.objects.create(
            copy=clean_code_copy,
            member=stu1_profile,
            issued_by=lib_user,
            issue_date=today - timedelta(days=4),
            due_date=today + timedelta(days=10),
            notes="Standard course reference loan"
        )
        clean_code_copy.status = 'issued'
        clean_code_copy.save()

    # Loan 2: OVERDUE loan for Tanvir (Algorithms CLRS, due 3 days ago -> 15 BDT fine!)
    clrs_copy = BookCopy.objects.filter(book__title__icontains='Introduction to Algorithms', status='available').first()
    if clrs_copy and not Loan.objects.filter(copy=clrs_copy, returned_at__isnull=True).exists():
        Loan.objects.create(
            copy=clrs_copy,
            member=stu1_profile,
            issued_by=lib_user,
            issue_date=today - timedelta(days=17),
            due_date=today - timedelta(days=3),
            notes="Overdue loan demonstration for fine testing"
        )
        clrs_copy.status = 'issued'
        clrs_copy.save()

    # Loan 3: Active loan for Rahim (Data-Intensive Applications)
    ddia_copy = BookCopy.objects.filter(book__title__icontains='Data-Intensive', status='available').first()
    if ddia_copy and not Loan.objects.filter(copy=ddia_copy, returned_at__isnull=True).exists():
        Loan.objects.create(
            copy=ddia_copy,
            member=stu2_profile,
            issued_by=lib_user,
            issue_date=today - timedelta(days=13),
            due_date=today + timedelta(days=1),
            notes="Semester project research"
        )
        ddia_copy.status = 'issued'
        ddia_copy.save()

    # Loan 4: Returned historical loan
    prag_copy = BookCopy.objects.filter(book__title__icontains='Pragmatic Programmer').first()
    if prag_copy and not Loan.objects.filter(copy=prag_copy, returned_at__isnull=False).exists():
        Loan.objects.create(
            copy=prag_copy,
            member=stu1_profile,
            issued_by=lib_user,
            issue_date=today - timedelta(days=30),
            due_date=today - timedelta(days=16),
            returned_at=timezone.now() - timedelta(days=16),
            fine_amount=Decimal('0.00'),
            fine_paid=True,
            notes="Returned on time in pristine condition"
        )

    # 6. Demand Analytics Seeding: Reservations, Searches, and Surveys
    clean_code_book = Book.objects.filter(title__icontains='Clean Code').first()
    clrs_book = Book.objects.filter(title__icontains='Algorithms').first()
    ddia_book = Book.objects.filter(title__icontains='Data-Intensive').first()
    ai_book = Book.objects.filter(title__icontains='Artificial Intelligence').first()

    # Reservations
    if clean_code_book and not Reservation.objects.filter(book=clean_code_book).exists():
        Reservation.objects.create(book=clean_code_book, member=stu2_profile, status='pending', notes='Waiting for copy')
        Reservation.objects.create(book=clean_code_book, member=stu1_profile, status='pending', notes='Next in queue')
    if ddia_book and not Reservation.objects.filter(book=ddia_book).exists():
        Reservation.objects.create(book=ddia_book, member=stu1_profile, status='pending', notes='Research reserve')
    print("[OK] Sample waiting reservations created")

    # Search Logs
    for title, book_obj in [("Clean Code", clean_code_book), ("Algorithms", clrs_book), ("Python Crash", None), ("Data Intensive", ddia_book)]:
        for _ in range(3):
            SearchLog.objects.create(query=title, matched_book=book_obj)
    print("[OK] Sample search query logs created")

    # Survey Responses
    if not SurveyResponse.objects.exists():
        SurveyResponse.objects.create(
            student=stu1_profile,
            preferred_category=cat_map['se-arch'],
            unmet_subject="Clean Architecture & Design Patterns",
            unavailable_frequency="often",
            satisfaction_score=4,
            wants_recommendations=True,
            suggested_title="Clean Architecture by Robert C. Martin",
            suggestions="More physical copies for Clean Code and software architecture."
        )
        SurveyResponse.objects.create(
            student=stu2_profile,
            preferred_category=cat_map['db-cloud'],
            unmet_subject="Cloud Native Computing",
            unavailable_frequency="sometimes",
            satisfaction_score=5,
            wants_recommendations=True,
            suggested_title="Designing Data-Intensive Applications",
            suggestions="Add more books on Kubernetes and microservices."
        )
    print("[OK] Sample student survey responses created")

    # Security Audit Logs
    if not SecurityAuditLog.objects.exists():
        SecurityAuditLog.objects.create(
            user=admin_user,
            action='LOGIN_SUCCESS',
            ip_address='127.0.0.1',
            details="Initial administrator system provisioning and security setup"
        )
        SecurityAuditLog.objects.create(
            user=lib_user,
            action='LOGIN_SUCCESS',
            ip_address='127.0.0.1',
            details="Librarian logged in to circulation desk"
        )
    print("[OK] Security audit logs seeded")

    print("\n[SUCCESS] Database fully seeded with Users, Roles, Books, Copies, Demand Analytics & Security Logs!")

if __name__ == '__main__':
    seed_database()
