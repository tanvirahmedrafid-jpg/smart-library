"""
S-liBro: Librarian AI Command Assistant Service
Interprets natural language commands (English & Bangla) to manage catalogue records
and physical copies with strict validation and two-step confirmation.
"""

import json
import logging
import os
import re
import urllib.error
import urllib.request
from django.conf import settings
from catalog.models import Book, BookCopy, Category

logger = logging.getLogger(__name__)

BENGALI_TO_ENGLISH_DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')

def normalize_digits(text):
    if not text:
        return ""
    return str(text).translate(BENGALI_TO_ENGLISH_DIGITS)

def get_available_categories():
    categories = list(Category.objects.all().values('id', 'name', 'slug'))
    return categories

def find_best_category_match(cat_str, categories):
    if not cat_str:
        return None
    cat_str_clean = cat_str.strip().lower()
    for c in categories:
        if c['name'].lower() in cat_str_clean or cat_str_clean in c['name'].lower() or c['slug'] in cat_str_clean:
            return c
    # Fallback keyword matching
    keyword_map = {
        'programming': 'Computer Science',
        'software': 'Computer Science',
        'algorithm': 'Computer Science',
        'data': 'Computer Science',
        'code': 'Computer Science',
        'ai': 'Computer Science',
        'business': 'Business',
        'finance': 'Business',
        'management': 'Business',
        'literature': 'Literature',
        'english': 'Literature',
        'novel': 'Literature',
        'science': 'Science',
        'physics': 'Science',
        'math': 'Science'
    }
    for kw, target in keyword_map.items():
        if kw in cat_str_clean:
            for c in categories:
                if c['name'].lower() == target.lower():
                    return c
    return None

def fallback_command_parser(command_text, categories):
    """
    High-accuracy local rule-based regex & NLP parser for English and Bengali commands.
    Ensures the Librarian Command Assistant works reliably even when Gemini API is offline or unconfigured.
    """
    text = command_text.strip()
    norm_text = normalize_digits(text)
    lower_text = norm_text.lower()

    fields = {
        'title': '',
        'author': '',
        'isbn': '',
        'category_id': '',
        'category_name': '',
        'publisher': '',
        'edition': '1st Edition',
        'shelf_location': 'Rack CS-01, Shelf A',
        'description': '',
        'cover_theme': 'cover-blue',
        'copies_count': 1
    }
    action = 'add_book'
    missing_fields = []

    # 1. Detect Action
    if any(k in lower_text for k in ['search', 'find', 'lookup', 'খুঁজ', 'সন্ধান', 'দেখাও']):
        action = 'search_book'
    elif any(k in lower_text for k in ['add copy', 'add copies', 'more copies', 'কপি যোগ', 'কপি বাড়াও', 'কপি বৃদ্ধি']):
        action = 'add_copies'
    elif any(k in lower_text for k in ['update', 'edit', 'change', 'আপডেট', 'পরিবর্তন']):
        action = 'update_book'
    else:
        action = 'add_book'

    # 2. Extract Copies Count
    copies_match = re.search(r'(\d+)\s*(?:copies|copy|কপি)', norm_text, re.IGNORECASE)
    if copies_match:
        try:
            fields['copies_count'] = max(1, min(50, int(copies_match.group(1))))
        except ValueError:
            fields['copies_count'] = 1

    # 3. Extract ISBN
    isbn_match = re.search(r'(?:isbn|আইএসবিএন)\s*[:=]?\s*([0-9Xx\-]{9,17})', norm_text, re.IGNORECASE)
    if isbn_match:
        fields['isbn'] = isbn_match.group(1).strip()
    else:
        # Fallback raw 10 or 13 digits ISBN
        raw_isbn = re.search(r'\b(97[89][0-9\-]{10,14}|[0-9]{9}[0-9Xx])\b', norm_text)
        if raw_isbn:
            fields['isbn'] = raw_isbn.group(1).strip()

    # 4. Extract Shelf Location
    shelf_match = re.search(r'(?:shelf(?:\s*location)?|র‍্যাক|শেলফ)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:isbn|category|publisher|edition|author|desc)|$)', text, re.IGNORECASE)
    if shelf_match:
        fields['shelf_location'] = shelf_match.group(1).strip()

    # 5. Extract Publisher
    pub_match = re.search(r'(?:publisher|প্রকাশক)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:isbn|category|shelf|edition|author|desc)|$)', text, re.IGNORECASE)
    if pub_match:
        fields['publisher'] = pub_match.group(1).strip()

    # 6. Extract Edition
    ed_match = re.search(r'(?:edition|সংস্করণ)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:isbn|category|shelf|publisher|author|desc)|$)', text, re.IGNORECASE)
    if ed_match:
        raw_ed = ed_match.group(1).strip()
        if re.match(r'^\d+$', raw_ed):
            fields['edition'] = f"{raw_ed}th Edition"
        else:
            fields['edition'] = raw_ed

    # 7. Extract Category
    cat_match = re.search(r'(?:category|বিষয়|ক্যাটাগরি)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:isbn|shelf|publisher|edition|author|desc)|$)', text, re.IGNORECASE)
    if cat_match:
        matched_cat = find_best_category_match(cat_match.group(1), categories)
        if matched_cat:
            fields['category_id'] = matched_cat['id']
            fields['category_name'] = matched_cat['name']
    if not fields['category_id'] and categories:
        # Try finding any category name mentioned in whole text
        matched_cat = find_best_category_match(text, categories)
        if matched_cat:
            fields['category_id'] = matched_cat['id']
            fields['category_name'] = matched_cat['name']
        else:
            fields['category_id'] = categories[0]['id']
            fields['category_name'] = categories[0]['name']

    # 8. Extract Title & Author
    # Pattern A: Bangla colon syntax "যোগ করো: Title, লেখক Author"
    bn_colon_match = re.search(
        r'(?:যোগ\s*করো|নতুন\s*বই|বই\s*যোগ)[^:]*:\s*([^,;]+?)(?:,\s*(?:লেখক|author|isbn|আইএসবিএন|বিভাগ|category)|$)',
        text, re.IGNORECASE
    )
    if bn_colon_match:
        fields['title'] = bn_colon_match.group(1).strip()

    # Pattern B: "লেখক Name" for Bangla author
    bn_author_match = re.search(
        r'(?:লেখক|লেখকঃ)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:আইএসবিএন|isbn|বিভাগ|category|শেলফ|shelf|title)|$)',
        text, re.IGNORECASE
    )
    if bn_author_match:
        fields['author'] = bn_author_match.group(1).strip()

    # Pattern C: "Add [N copies of] [Title] by [Author]" (English)
    if not fields['title']:
        add_by_match = re.search(
            r'(?:add|insert)?\s*(?:\d+\s*(?:copies|copy)\s*of\s*)?([^,;]+?)\s+by\s+([^,;]+)',
            text, re.IGNORECASE
        )
        if add_by_match:
            raw_title = add_by_match.group(1).strip()
            raw_title = re.sub(r'^(?:add|insert)\s*', '', raw_title, flags=re.IGNORECASE).strip()
            raw_title = re.sub(r'^\d+\s*(?:copies|copy)\s*of\s*', '', raw_title, flags=re.IGNORECASE).strip()
            if raw_title:
                fields['title'] = raw_title
            if not fields['author']:
                fields['author'] = add_by_match.group(2).strip()

    # Pattern D: Named parameter extraction (English)
    if not fields['title']:
        title_match = re.search(
            r'(?:title|book)\s*[:=]?\s*([^,;]+?)(?:,\s*(?:author|isbn|category|shelf|publisher)|$)',
            text, re.IGNORECASE
        )
        if title_match:
            fields['title'] = title_match.group(1).strip()
    if not fields['author']:
        author_match = re.search(
            r'author\s*[:=]?\s*([^,;]+?)(?:,\s*(?:title|isbn|category|shelf|publisher)|$)',
            text, re.IGNORECASE
        )
        if author_match:
            fields['author'] = author_match.group(1).strip()

    # Search query fallback
    if action == 'search_book' and not fields['title']:
        search_term = re.sub(r'^(?:search|find|lookup|খুঁজো|দেখাও)\s*(?:for|বই)?\s*', '', text, flags=re.IGNORECASE).strip()
        fields['title'] = search_term

    # Validate essential fields
    if not fields['title']:
        missing_fields.append('title')
    if action == 'add_book':
        if not fields['author']:
            missing_fields.append('author')
        if not fields['isbn']:
            missing_fields.append('isbn')

    msg = f"Interpreted command to {action.replace('_', ' ')}."
    if missing_fields:
        msg += f" Please supply missing details: {', '.join(missing_fields)}."

    return {
        'action': action if not missing_fields else ('need_info' if not fields['title'] else action),
        'message': msg,
        'missing_fields': missing_fields,
        'fields': fields,
        'is_gemini': False
    }

def call_gemini_for_command(command_text, categories):
    """
    Calls Google Gemini Developer API to parse natural-language librarian commands into structured JSON.
    """
    from library.services.gemini import get_gemini_config, GEMINI_API_URL_TEMPLATE
    api_key, model, timeout = get_gemini_config()
    if not api_key:
        return None

    cat_list_str = "\n".join([f"- ID: {c['id']}, Name: '{c['name']}' (slug: {c['slug']})" for c in categories])

    system_prompt = (
        "You are an AI Librarian Assistant for S-liBro University Library Management System. "
        "The librarian enters a natural-language command in English or Bengali to manage books.\n"
        "Your task is to parse the command into a STRICT JSON response.\n\n"
        "AVAILABLE SYSTEM CATEGORIES:\n"
        f"{cat_list_str}\n\n"
        "JSON SCHEMA SPECIFICATION:\n"
        "{\n"
        '  "action": "add_book" | "add_copies" | "update_book" | "search_book" | "need_info",\n'
        '  "message": "Friendly, short explanation of the interpreted action in the same language as the command (English or Bengali).",\n'
        '  "missing_fields": ["title", "author", ...],\n'
        '  "fields": {\n'
        '    "title": "string (capitalized book title)",\n'
        '    "author": "string (author names)",\n'
        '    "isbn": "string (with dashes or numbers, e.g. 978-0132350884)",\n'
        '    "category_id": integer (must match one of the available category IDs above, or null),\n'
        '    "category_name": "string",\n'
        '    "publisher": "string",\n'
        '    "edition": "string (e.g. 1st Edition, 2nd Edition)",\n'
        '    "shelf_location": "string (e.g. Rack A-1, Shelf 3)",\n'
        '    "description": "string (brief summary or subject)",\n'
        '    "cover_theme": "cover-blue" | "cover-orange" | "cover-sage" | "cover-purple" | "cover-rose" | "cover-sand",\n'
        '    "copies_count": integer (number of physical copies to add, default 1)\n'
        "  }\n"
        "}\n\n"
        "CRITICAL RULES:\n"
        "- If required fields (e.g., author or ISBN for a new book) are not provided in the command, leave them as empty strings and list them in missing_fields.\n"
        "- NEVER invent or hallucinate ISBN numbers or authors. If absent, leave empty.\n"
        "- Return ONLY the raw JSON object. Do not enclose in markdown code blocks if possible, or return strictly parseable JSON."
    )

    url = f"{GEMINI_API_URL_TEMPLATE.format(model=model)}?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nLibrarian Command: {command_text.strip()}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 600,
            "responseMimeType": "application/json"
        }
    }

    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            candidates = res_json.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                raw_reply = "".join(p.get('text', '') for p in parts).strip()
                # Clean any markdown fences if present
                clean_json_str = re.sub(r'^```json\s*', '', raw_reply)
                clean_json_str = re.sub(r'```$', '', clean_json_str).strip()
                parsed = json.loads(clean_json_str)
                parsed['is_gemini'] = True
                return parsed
    except Exception as e:
        logger.warning("Gemini Command Parser failed, falling back to local NLP parser: %s", str(e))
        return None

def interpret_librarian_command(command_text):
    """
    Interprets natural language librarian commands.
    Verifies existing books in the database to detect ISBN duplicates,
    suggests adding copies or updates, and returns a verified preview payload.
    """
    clean_text = (command_text or "").strip()
    if not clean_text:
        return {
            'success': False,
            'message': "Please enter a command. Example: 'Add 3 copies of Clean Architecture by Robert C. Martin, ISBN 978-0134494166, shelf Rack A-2'",
            'fields': {}
        }

    categories = get_available_categories()

    # 1. Try Gemini AI parsing if key available
    parsed = call_gemini_for_command(clean_text, categories)

    # 2. If Gemini unavailable, use local robust parser
    if not parsed:
        parsed = fallback_command_parser(clean_text, categories)

    fields = parsed.get('fields', {})
    action = parsed.get('action', 'add_book')
    missing_fields = parsed.get('missing_fields', [])

    # Ensure integer copies_count
    try:
        fields['copies_count'] = max(1, min(50, int(fields.get('copies_count') or 1)))
    except (ValueError, TypeError):
        fields['copies_count'] = 1

    # Ensure category validity
    cat_id = fields.get('category_id')
    valid_cat = None
    if cat_id:
        valid_cat = Category.objects.filter(id=cat_id).first()
    if not valid_cat and fields.get('category_name'):
        valid_cat = find_best_category_match(fields['category_name'], categories)
    if valid_cat:
        fields['category_id'] = valid_cat.id
        fields['category_name'] = valid_cat.name
    elif categories:
        fields['category_id'] = categories[0]['id']
        fields['category_name'] = categories[0]['name']

    # 3. Database Check: Check for Existing Book by ISBN or Title
    existing_book = None
    isbn_clean = (fields.get('isbn') or '').strip()
    if isbn_clean:
        # Match exact ISBN or normalized ISBN without dashes
        existing_book = Book.objects.filter(isbn__iexact=isbn_clean).first()
        if not existing_book:
            norm_isbn = re.sub(r'[^0-9Xx]', '', isbn_clean)
            for b in Book.objects.all():
                if re.sub(r'[^0-9Xx]', '', b.isbn) == norm_isbn:
                    existing_book = b
                    break

    if not existing_book and fields.get('title'):
        title_q = fields['title'].strip()
        existing_book = Book.objects.filter(title__iexact=title_q).first()

    existing_book_info = None
    if existing_book:
        existing_book_info = {
            'id': existing_book.id,
            'title': existing_book.title,
            'author': existing_book.author,
            'isbn': existing_book.isbn,
            'category_id': existing_book.category_id,
            'category_name': existing_book.category.name if existing_book.category else 'General',
            'publisher': existing_book.publisher,
            'edition': existing_book.edition,
            'shelf_location': existing_book.shelf_location,
            'copies_count': existing_book.total_copies_count,
            'available_count': existing_book.available_copies_count,
            'url': f"/books/{existing_book.id}/"
        }

        # If librarian typed "add book" but ISBN exists, notify them
        if action == 'add_book':
            parsed['message'] = (
                f"Notice: A book with this title/ISBN is already in the catalogue ('{existing_book.title}'). "
                f"You can choose to add {fields['copies_count']} copy/copies to the existing title, or update its details."
            )

    return {
        'success': True,
        'action': action,
        'message': parsed.get('message', 'Command interpreted successfully.'),
        'missing_fields': missing_fields,
        'fields': fields,
        'existing_book': existing_book_info,
        'ai_powered': parsed.get('is_gemini', False),
        'ai_engine': "Google Gemini" if parsed.get('is_gemini') else "S-liBro Local NLP Engine"
    }

def execute_librarian_command(user, payload):
    """
    Executes a confirmed librarian command.
    Performs server-side validation, writes to Book and BookCopy models,
    and returns immediate confirmation details.
    """
    action = payload.get('action', 'add_book')
    fields = payload.get('fields', {})

    title = (fields.get('title') or '').strip()
    author = (fields.get('author') or '').strip()
    isbn = (fields.get('isbn') or '').strip()
    copies_count = int(fields.get('copies_count') or 1)
    copies_count = max(1, min(50, copies_count))

    # For add_copies, title is not required when book_id or isbn is supplied
    if not title and action not in ('add_copies', 'update_book'):
        return {'success': False, 'error': 'Book title is required.'}

    # 1. ADD COPIES TO EXISTING BOOK
    if action == 'add_copies':
        book_id = payload.get('book_id') or (fields.get('id') if isinstance(fields, dict) else None)
        book = None
        if book_id:
            book = Book.objects.filter(id=book_id).first()
        if not book and isbn:
            book = Book.objects.filter(isbn__iexact=isbn).first()
        if not book:
            book = Book.objects.filter(title__iexact=title).first()

        if not book:
            return {'success': False, 'error': f"Could not find existing book '{title}' to add copies."}

        current_copies = book.copies.count()
        cat_prefix = book.category.slug[:4].upper() if book.category else 'GEN'
        new_copies = []
        for i in range(current_copies + 1, current_copies + copies_count + 1):
            copy_code = f"SLM-{cat_prefix}-{book.id:03d}-C{i}"
            c = BookCopy.objects.create(
                book=book,
                copy_code=copy_code,
                status='available',
                condition='new'
            )
            new_copies.append(copy_code)

        return {
            'success': True,
            'action_executed': 'add_copies',
            'message': f"Added {copies_count} new copy/copies to '{book.title}'!",
            'book_id': book.id,
            'book_title': book.title,
            'total_copies': book.total_copies_count,
            'available_copies': book.available_copies_count,
            'new_copies': new_copies,
            'redirect_url': f"/books/{book.id}/"
        }

    # 2. UPDATE EXISTING BOOK
    elif action == 'update_book':
        book_id = payload.get('book_id') or (fields.get('id') if isinstance(fields, dict) else None)
        book = None
        if book_id:
            book = Book.objects.filter(id=book_id).first()
        if not book and isbn:
            book = Book.objects.filter(isbn__iexact=isbn).first()

        if not book:
            return {'success': False, 'error': f"Could not find book to update."}

        if title:
            book.title = title
        if author:
            book.author = author
        if fields.get('category_id'):
            cat = Category.objects.filter(id=fields['category_id']).first()
            if cat:
                book.category = cat
        if fields.get('publisher'):
            book.publisher = fields['publisher']
        if fields.get('edition'):
            book.edition = fields['edition']
        if fields.get('shelf_location'):
            book.shelf_location = fields['shelf_location']
        if fields.get('description'):
            book.description = fields['description']
        if fields.get('cover_theme'):
            book.cover_theme = fields['cover_theme']

        book.save()
        return {
            'success': True,
            'action_executed': 'update_book',
            'message': f"Successfully updated bibliographic details for '{book.title}'.",
            'book_id': book.id,
            'book_title': book.title,
            'redirect_url': f"/books/{book.id}/"
        }

    # 3. ADD NEW BOOK & PHYSICAL COPIES
    elif action == 'add_book':
        if not author:
            return {'success': False, 'error': 'Author name is required to add a new book.'}
        if not isbn:
            return {'success': False, 'error': 'ISBN is required to add a new book.'}

        # Duplicate ISBN check
        if Book.objects.filter(isbn__iexact=isbn).exists():
            existing = Book.objects.filter(isbn__iexact=isbn).first()
            return {
                'success': False,
                'duplicate_isbn': True,
                'error': f"A book with ISBN '{isbn}' already exists: '{existing.title}'. Would you like to add copies instead?",
                'existing_book_id': existing.id
            }

        cat = None
        if fields.get('category_id'):
            cat = Category.objects.filter(id=fields['category_id']).first()
        if not cat:
            cat = Category.objects.first()

        book = Book.objects.create(
            title=title,
            author=author,
            isbn=isbn,
            category=cat,
            publisher=fields.get('publisher', ''),
            edition=fields.get('edition', '1st Edition'),
            shelf_location=fields.get('shelf_location', 'Rack CS-01, Shelf A'),
            description=fields.get('description', ''),
            cover_theme=fields.get('cover_theme', 'cover-blue')
        )

        cat_prefix = cat.slug[:4].upper() if cat else 'GEN'
        new_copies = []
        for i in range(1, copies_count + 1):
            copy_code = f"SLM-{cat_prefix}-{book.id:03d}-C{i}"
            BookCopy.objects.create(
                book=book,
                copy_code=copy_code,
                status='available',
                condition='new'
            )
            new_copies.append(copy_code)

        return {
            'success': True,
            'action_executed': 'add_book',
            'message': f"Book '{book.title}' created successfully with {copies_count} barcode-tracked copies!",
            'book_id': book.id,
            'book_title': book.title,
            'total_copies': book.total_copies_count,
            'available_copies': book.available_copies_count,
            'new_copies': new_copies,
            'redirect_url': f"/books/{book.id}/"
        }

    return {'success': False, 'error': f"Unknown action: {action}"}
