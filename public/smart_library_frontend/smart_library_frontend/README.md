# Smart Library website frontend

Responsive Django-template frontend for the Smart Library Management System proposal. The interface includes a public home page and catalogue plus member and librarian workspaces. The book artwork is drawn with CSS, so the starter works without downloading image files; real uploaded cover images are used when `book.cover_image` is present.

## Pages included

- `home.html` — hero, search, collection statistics, featured books
- `catalog.html` — search, category filter, availability filter, sorting, pagination
- `book_detail.html` — book information, availability, reference value, login/borrow link
- `login.html` — member login form
- `member_dashboard.html` — active loans, due dates, fine summary, history
- `staff_dashboard.html` — catalogue metrics, overdue loans, quick actions, circulation chart
- `books.html` — book/copy list and add/edit form area
- `members.html` — member directory and register/edit form area
- `circulation.html` — issue and return forms plus recent loans
- `reports.html` — inventory, loans, overdue, and member report views

## Add these files to your Django project

Copy the `templates/library/` folder into your project's templates directory. Copy `static/library_ui/` into your static files directory. For example:

```text
project/
├── templates/
│   └── library/           # copy this package's templates/library here
└── static/
    └── library_ui/        # copy this package's static/library_ui here
```

In `settings.py`, make sure Django can find project templates and static files:

```python
TEMPLATES = [
    {
        # Keep the other generated settings here.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        # Keep the generated context processors.
    },
]
STATIC_URL = "static/"
```

The base template uses Django's `{% static %}` tag and named URL routes. Define routes with these names (or change the `{% url %}` tags to match your existing route names):

```text
home, catalog, book_detail, login, logout,
member_dashboard, staff_dashboard,
books, book_create, book_edit,
members, member_edit,
circulation, issue_book, return_book,
reports, report_csv
```

The `books` view can render `library/books.html` for the list, create, and edit states. Pass `book_form` when showing the form. The `members` view can do the same with `member_form`.

## Template context expected

Pass the following values from Django views. Missing list values render an empty state. Demo numbers and the homepage fallback covers are illustrative only.

| Page | Main context |
|---|---|
| Home | `stats` (`total_titles`, `available_copies`, `active_members`), `featured_books` or `demo_books` |
| Catalogue | `books`, `categories`, `page_obj`, `is_paginated`, `demo_books` (optional), plus the normal `request` context processor |
| Book detail | `book` |
| Member dashboard | `stats`, `loans`, `history` |
| Staff dashboard | `stats`, `overdue_loans`, `chart_data` |
| Books | `books`, `page_obj`, optional `book_form` |
| Members | `members`, `page_obj`, optional `member_form` |
| Circulation | `active_members`, `available_copies`, `active_loans`, `recent_loans`, `settings` |
| Reports | `stats`, `report_title`, `report_updated`, `report_rows` |

Use Django's login-required and permission checks in the views for private pages. Hiding a navigation link in a template is not an access-control check. The template expects `user`, `messages`, and `request` in the standard Django context processors.

## Book fields used by the interface

The catalogue expects a `book` object with `title`, `author`, `isbn`, `category`, `description`, `shelf_location`, `available_copies`, and optional `cover_image`. For the requested price display, it reads `book.price`, then `book.replacement_price`. In a library system this should be treated as an inventory or replacement value, not a price for selling a library book. It is optional and should be added to the Django model if you want to store it:

```python
price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
cover_image = models.ImageField(upload_to="book_covers/", null=True, blank=True)
cover_style = models.CharField(max_length=20, default="sage")
```

If you add `ImageField`, install Pillow and configure `MEDIA_URL` / `MEDIA_ROOT`. The CSS-made covers continue to display when no image is uploaded. Supported cover color names include `sage`, `blue`, `orange`, `purple`, `rose`, and `sand`.

## Forms and backend connection

The issue form posts `member_id` and `copy_id` to `issue_book`. The return form posts `loan_id` to `return_book`. Both include CSRF tokens. Connect them to Django views that validate member status, copy availability, active-loan limits, return state, due dates, and fines before saving. The templates do not implement those backend rules.

The login template posts `username` and `password`; connect it to Django's authentication view or a compatible view. Logout uses a CSRF-protected POST form.

## Design notes

- Responsive layout for desktop and mobile screens.
- CSS-created three-dimensional book stacks and illustrated covers; no third-party image dependency.
- Uses Google Fonts when online and falls back to system sans-serif fonts offline.
- Prices are sample/reference display values only. Replace demo data with database values before presenting the website.
