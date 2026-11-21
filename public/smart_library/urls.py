from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from catalog import views as catalog_views
from accounts import views as accounts_views
from circulation import views as circulation_views
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public & Catalogue
    path('', catalog_views.home_view, name='home'),
    path('catalog/', catalog_views.catalog_view, name='catalog'),
    path('books/<int:pk>/', catalog_views.book_detail_view, name='book_detail'),

    # Authentication & Members
    path('login/', accounts_views.login_view, name='login'),
    path('logout/', accounts_views.logout_view, name='logout'),
    path('dashboard-redirect/', accounts_views.dashboard_redirect, name='dashboard_redirect'),
    path('members/', accounts_views.members_view, name='members'),
    path('members/<int:pk>/edit/', accounts_views.member_edit_view, name='member_edit'),

    # Catalogue Management (Staff)
    path('books/', catalog_views.books_manage_view, name='books'),
    path('books/create/', catalog_views.book_create_view, name='book_create'),
    path('books/<int:pk>/edit/', catalog_views.book_edit_view, name='book_edit'),
    path('books/ai-command/interpret/', catalog_views.librarian_interpret_command_api, name='librarian_ai_interpret'),
    path('books/ai-command/execute/', catalog_views.librarian_execute_command_api, name='librarian_ai_execute'),

    # Circulation (Issue / Return / Renew)
    path('circulation/', circulation_views.circulation_view, name='circulation'),
    path('circulation/issue/', circulation_views.issue_book_view, name='issue_book'),
    path('circulation/return/', circulation_views.return_book_view, name='return_book'),
    path('circulation/renew/<int:pk>/', circulation_views.renew_book_view, name='renew_book'),

    # Distinct Portals
    path('my-library/', dashboard_views.member_dashboard_view, name='member_dashboard'),
    path('staff-desk/', dashboard_views.staff_dashboard_view, name='staff_dashboard'),
    path('admin-portal/', dashboard_views.admin_portal_view, name='admin_portal'),
    path('admin-portal/backup-db/', dashboard_views.admin_download_db_backup, name='admin_download_db_backup'),

    # Reports
    path('reports/', dashboard_views.reports_view, name='reports'),
    path('reports/csv/', dashboard_views.report_csv_view, name='report_csv'),

    # Smart AI API Endpoints
    path('ai/', include('smart_ai.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
