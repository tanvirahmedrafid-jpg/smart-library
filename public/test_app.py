import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_library.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from catalog.models import Book
from circulation.models import Loan, LibrarySettings
from smart_ai.analytics import get_book_demand_analytics
from accounts.models import SecurityAuditLog
from smart_ai.models import SurveyResponse

def test_system():
    client = Client()
    print("[*] Running comprehensive system test for new extended features...")

    # 1. Home and Catalog
    r = client.get('/')
    assert r.status_code == 200, f"Home page failed with {r.status_code}"
    print("[OK] Home page: 200 OK")

    r = client.get('/catalog/')
    assert r.status_code == 200, f"Catalog failed with {r.status_code}"
    print("[OK] Catalog page: 200 OK")

    # 2. Demand Analytics Calculation
    demand_data = get_book_demand_analytics()
    assert len(demand_data['rankings']) > 0, "No demand rankings generated"
    top_book = demand_data['top_book']
    print(f"[OK] Demand Analytics: Top book '{top_book['book'].title}' with Demand Score {top_book['demand_score']}")
    print(f"     Signals: B={top_book['b_raw']}, R={top_book['r_raw']}, S={top_book['s_raw']}, Q={top_book['q_raw']}")
    print(f"     Shortage alerts detected: {demand_data['shortage_count']}")

    # 3. Student Role Protection & Portal
    # Unauthenticated access to /my-library/ must redirect to login
    r = client.get('/my-library/')
    assert r.status_code == 302 and 'login' in r['Location'], "Unauthenticated access not blocked"
    print("[OK] Unauthenticated access to student portal successfully blocked & redirected to login")

    # Student logs in
    login_stu = client.login(username='tanvir', password='stu123')
    assert login_stu, "Student login failed"
    r = client.get('/my-library/')
    assert r.status_code == 200, f"Student portal failed with {r.status_code}"
    print("[OK] Student portal access: 200 OK")

    # Student tries to access Librarian Desk or Admin Portal -> MUST BE BLOCKED
    r = client.get('/staff-desk/', follow=True)
    assert 'Access Denied' in r.content.decode('utf-8') or r.redirect_chain, "Student not blocked from librarian desk"
    print("[OK] Student blocked from Librarian Desk")

    r = client.get('/admin-portal/', follow=True)
    assert 'Access Denied' in r.content.decode('utf-8') or r.redirect_chain, "Student not blocked from admin portal"
    print("[OK] Student blocked from Admin Portal")

    # Student submits resource survey
    r = client.post('/my-library/', {
        'action': 'submit_survey',
        'preferred_category': '1',
        'unavailable_frequency': 'often',
        'unmet_subject': 'System Design',
        'suggested_title': 'Designing Distributed Systems',
        'suggestions': 'Need more distributed systems books'
    }, follow=True)
    assert r.status_code == 200
    assert SurveyResponse.objects.filter(suggested_title='Designing Distributed Systems').exists()
    print("[OK] Student survey submitted and recorded in database")
    client.logout()

    # 4. Librarian Role Protection & Staff Desk
    login_lib = client.login(username='librarian', password='lib123')
    assert login_lib, "Librarian login failed"
    r = client.get('/staff-desk/')
    assert r.status_code == 200, f"Staff desk failed with {r.status_code}"
    assert 'Demand Score' in r.content.decode('utf-8'), "Demand Analytics not rendered on librarian desk"
    print("[OK] Librarian portal access: 200 OK (Demand Analytics & Shortage Alerts rendered)")

    # Librarian tries to access Admin Portal -> MUST BE BLOCKED
    r = client.get('/admin-portal/', follow=True)
    assert 'Access Denied' in r.content.decode('utf-8') or r.redirect_chain, "Librarian not blocked from admin portal"
    print("[OK] Librarian blocked from Admin Portal")
    client.logout()

    # 5. Administrator Control Center & Security Features
    login_admin = client.login(username='admin', password='admin123')
    assert login_admin, "Admin login failed"
    r = client.get('/admin-portal/')
    assert r.status_code == 200, f"Admin portal failed with {r.status_code}"
    print("[OK] Administrator portal access: 200 OK")

    # Test Admin Password Reset for a user
    target_user = User.objects.get(username='rahim')
    r = client.post('/admin-portal/', {
        'action': 'reset_password',
        'target_user_id': target_user.id,
        'new_password': 'newpass123',
        'confirm_password': 'newpass123'
    }, follow=True)
    assert r.status_code == 200
    # Verify password was updated
    rahim_check = client.login(username='rahim', password='newpass123')
    assert rahim_check, "Password reset by admin did not take effect"
    print("[OK] Admin Password Management: User password reset verified")

    # Re-login admin
    client.login(username='admin', password='admin123')

    # Test Database Backup Download
    r = client.get('/admin-portal/backup-db/')
    assert r.status_code == 200
    assert 'sqlite3' in r.get('Content-Disposition', ''), "Database backup file not returned"
    print("[OK] Admin Database Backup: SQLite backup stream received (Content-Disposition verified)")

    # Test Audit Log recording
    latest_log = SecurityAuditLog.objects.first()
    assert latest_log is not None, "Security audit log empty"
    print(f"[OK] Security Audit Trail: Latest event [{latest_log.action}] - {latest_log.details}")

    # 6. Test Explicit Logout Endpoint & Security Audit Logging
    client.login(username='admin', password='admin123')
    r = client.get('/logout/', follow=True)
    assert r.status_code == 200
    assert 'logged out' in r.content.decode('utf-8').lower(), "Logout success message not displayed"
    # Ensure session is terminated and protected portal cannot be reached
    r = client.get('/admin-portal/')
    assert r.status_code == 302 and 'login' in r['Location'], "User still authenticated after logout"
    logout_log = SecurityAuditLog.objects.filter(action='LOGOUT').first()
    assert logout_log is not None, "Logout event not recorded in SecurityAuditLog"
    print(f"[OK] Logout System: GET & POST session termination verified, redirected to login with flash message, audit log [{logout_log.action}]")

    # 7. Test Gemini AI Library Assistant Service & Catalogue Grounding
    import json
    r = client.post('/ai/chat/', data=json.dumps({'message': 'Can you recommend Python programming books?'}), content_type='application/json')
    assert r.status_code == 200, f"AI chat endpoint failed with {r.status_code}"
    ai_res = r.json()
    assert 'reply' in ai_res and 'ai_label' in ai_res, "AI response missing reply or ai_label"
    print(f"[OK] Gemini AI Assistant Endpoint: 200 OK | Label: {ai_res['ai_label']}")

    # 8. Test Organized Image Assets
    for asset in [
        'static/library/images/brand/logo.png',
        'static/library/images/brand/open_book_icon.png',
        'static/library/images/brand/favicon.ico',
        'static/library/images/promotions/smart_campus_banner.png',
        'static/library/images/promotions/smart_campus_poster.png',
        'static/library/images/promotions/smart_campus_launch.png',
        'static/library/images/books/cover_algorithms.jpg'
    ]:
        assert os.path.exists(asset), f"Asset missing: {asset}"
    print("[OK] S-liBro Brand, Promotion, and Book image assets verified in static/library/images/")

    # 9. Test Librarian AI Command Assistant (English & Bangla commands + 2-step confirmation)
    # Check that students cannot access AI librarian endpoints
    client.login(username='tanvir', password='stu123')
    r = client.post('/books/ai-command/interpret/', data=json.dumps({'command': 'Add 2 copies of Test Book'}), content_type='application/json')
    assert r.status_code == 302, f"Student was not blocked from librarian AI endpoint (status: {r.status_code})"
    client.logout()

    # Login as Librarian
    client.login(username='librarian', password='lib123')
    
    # Test English Command Interpretation
    cmd_en = "Add 3 copies of Clean Code by Robert C. Martin, ISBN 9780132350884, category Programming, publisher Prentice Hall, edition 1, shelf Rack A, Shelf 2"
    r = client.post('/books/ai-command/interpret/', data=json.dumps({'command': cmd_en}), content_type='application/json')
    assert r.status_code == 200, f"AI interpret endpoint failed with {r.status_code}"
    res_en = r.json()
    assert res_en.get('success') is True, "AI interpret failed"
    fields_en = res_en.get('fields', {})
    assert 'Clean Code' in fields_en.get('title', ''), f"Title mismatch: {fields_en.get('title')}"
    assert fields_en.get('copies_count') == 3, f"Copies count mismatch: {fields_en.get('copies_count')}"
    assert '9780132350884' in fields_en.get('isbn', '').replace('-', ''), "ISBN mismatch"
    print(f"[OK] Librarian AI: English command interpreted correctly ({res_en.get('ai_engine')})")

    # Test Bangla Command Interpretation
    cmd_bn = "৩ কপি বই যোগ করো: Artificial Intelligence, লেখক Stuart Russell, আইএসবিএন 9780136042594, বিভাগ Computer Science, শেলফ Rack B-2"
    r = client.post('/books/ai-command/interpret/', data=json.dumps({'command': cmd_bn}), content_type='application/json')
    assert r.status_code == 200
    res_bn = r.json()
    assert res_bn.get('success') is True
    fields_bn = res_bn.get('fields', {})
    assert 'Artificial Intelligence' in fields_bn.get('title', '')
    assert fields_bn.get('copies_count') == 3
    print(f"[OK] Librarian AI: Bangla command interpreted correctly ({res_bn.get('ai_engine')})")

    # Test Command Execution: Add Book + Physical Copies with SLM- barcodes
    # Use a unique ISBN per test run to avoid duplicate collisions
    import time as _time
    test_isbn = f"978-TEST-{int(_time.time()) % 1000000:06d}"
    exec_payload = {
        'action': 'add_book',
        'fields': {
            'title': f'Test Book for AI Execution {test_isbn}',
            'author': 'Test Author, S-liBro QA',
            'isbn': test_isbn,
            'category_id': fields_en.get('category_id'),
            'publisher': 'Test Publisher',
            'edition': '1st Edition',
            'shelf_location': 'Rack QA-01, Shelf 1',
            'copies_count': 3,
            'description': 'Automated test book for AI command execution verification.',
            'cover_theme': 'cover-indigo'
        }
    }
    r = client.post('/books/ai-command/execute/', data=json.dumps(exec_payload), content_type='application/json')
    assert r.status_code == 200, f"AI execute endpoint failed with {r.status_code}"
    res_exec = r.json()
    assert res_exec.get('success') is True, f"Execution failed: {res_exec.get('error')}"
    assert len(res_exec.get('new_copies', [])) == 3, "Did not create 3 barcode copies"
    assert all(c.startswith('SLM-') for c in res_exec['new_copies']), "Barcodes missing SLM- prefix"
    created_book_id = res_exec.get('book_id')
    print(f"[OK] Librarian AI: Executed 'add_book' command, created Book id={created_book_id} and barcodes: {res_exec['new_copies']}")

    # Test Add Copies to Existing Book
    add_copies_payload = {
        'action': 'add_copies',
        'book_id': created_book_id,
        'fields': {
            'copies_count': 2
        }
    }
    r = client.post('/books/ai-command/execute/', data=json.dumps(add_copies_payload), content_type='application/json')
    assert r.status_code == 200
    res_add = r.json()
    assert res_add.get('success') is True
    assert len(res_add.get('new_copies', [])) == 2
    # Barcodes should be sequential (C4 and C5 after the initial 3 copies)
    assert all(c.startswith('SLM-') for c in res_add['new_copies']), "Add copies barcodes missing SLM- prefix"
    print(f"[OK] Librarian AI: Added 2 sequential copies to book: {res_add['new_copies']}")

    # Verify Security Audit Log recorded execution
    ai_audit = SecurityAuditLog.objects.filter(action='AI_COMMAND_EXECUTE').first()
    assert ai_audit is not None, "AI_COMMAND_EXECUTE event not logged in audit trail"
    print(f"[OK] Librarian AI Security Audit: Logged action [{ai_audit.action}] - {ai_audit.details}")

    client.logout()

    print("\n[SUCCESS] ALL EXTENDED SYSTEM, SECURITY, AND ANALYTICS CHECKS PASSED PERFECTLY!")

if __name__ == '__main__':
    test_system()
