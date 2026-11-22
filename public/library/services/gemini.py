"""
S-liBro: Gemini AI Library Assistant Service
Integrates Google Gemini Developer API (Google AI Studio Free Tier) with strict database grounding.
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from django.conf import settings
from catalog.models import Book, Category
from circulation.models import LibrarySettings

logger = logging.getLogger(__name__)

# Official Free-tier Model default
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def get_gemini_config():
    """
    Safely retrieve Gemini configuration from settings / environment.
    Never prints or exposes secret keys.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    api_key = api_key.strip()
    model = getattr(settings, 'GEMINI_MODEL', '') or os.environ.get('GEMINI_MODEL', '')
    model = (model or DEFAULT_GEMINI_MODEL).strip()
    timeout = getattr(settings, 'GEMINI_TIMEOUT_SECONDS', 10)
    return api_key, model, timeout

def format_catalog_context(max_books=35):
    """
    Fetches the existing catalogue as the single source of truth for the AI.
    Ensures Gemini cannot invent books or fake availability.
    """
    books = Book.objects.all().select_related('category')[:max_books]
    catalog_lines = []
    for b in books:
        cat_name = b.category.name if b.category else "General"
        avail = b.available_copies_count
        status = f"{avail} copy/copies available" if avail > 0 else "Currently on loan (0 available)"
        catalog_lines.append(
            f"- Title: \"{b.title}\" | Author: {b.author} | Category: {cat_name} | Shelf: {b.shelf_location} | Status: {status}"
        )
    return "\n".join(catalog_lines), list(books)

def match_books_in_text(text, book_list):
    """
    Matches titles mentioned in Gemini's answer to real database records.
    Returns list of verified book dictionaries.
    """
    matched = []
    text_lower = text.lower()
    for book in book_list:
        title_lower = book.title.lower()
        # Match full title or significant title prefix
        short_title = title_lower.split(':')[0].strip()
        if short_title in text_lower or title_lower in text_lower:
            matched.append({
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'category': book.category.name if book.category else 'General',
                'available': book.is_available,
                'available_count': book.available_copies_count,
                'shelf': book.shelf_location,
                'url': f"/books/{book.id}/"
            })
    return matched

def fallback_local_search(query_text, reason=None):
    """
    Graceful local fallback that searches the database directly
    when Gemini API key is missing, quota is reached, or network fails.
    """
    from smart_ai.chatbot import process_smart_assistant_query
    res = process_smart_assistant_query(query_text)
    
    prefix = ""
    if reason:
        prefix = f"> ℹ️ *{reason}*\n\n"
    
    return {
        'reply': prefix + res.get('reply', ''),
        'books': res.get('books', res.get('suggestions', [])),
        'quick_chips': res.get('quick_chips', ["Explore Catalog", "Borrowing Rules", "My Loans"]),
        'is_gemini': False,
        'ai_label': "S-liBro Catalogue Assistant (Local Verification)"
    }

def ask_gemini_library_assistant(user_query, user=None):
    """
    Main entry point for AI Library Assistant queries.
    Validates input, calls Gemini with grounded catalog, and falls back gracefully.
    """
    cleaned_query = (user_query or '').strip()
    
    # 1. Validation & Input Limiting
    if not cleaned_query:
        return {
            'reply': "Hello! I am **LibroAI**, your S-liBro Campus Assistant. How can I assist you with book recommendations, catalogue search, or borrowing policies today?",
            'books': [],
            'quick_chips': ["Search Computer Science", "Borrowing loan rules", "Recommend top books", "What is the fine rate?"],
            'is_gemini': False,
            'ai_label': "S-liBro Assistant"
        }
    
    # Limit input length to prevent token abuse and prompt injection
    if len(cleaned_query) > 300:
        cleaned_query = cleaned_query[:300]
    
    # Sanitize query against prompt injection attempts
    sanitized_query = re.sub(r'[\r\n]+', ' ', cleaned_query)
    
    api_key, model, timeout = get_gemini_config()
    catalog_context, book_list = format_catalog_context()
    lib_settings = LibrarySettings.get_settings()

    # 2. If API Key is missing: use graceful local catalog fallback
    if not api_key:
        return fallback_local_search(
            sanitized_query,
            reason="Gemini API key is not configured. Answering using direct campus database search."
        )

    # 3. Construct strictly grounded system prompt & user prompt
    system_instruction = (
        "You are the S-liBro AI Library Assistant for a university campus library. "
        "Your role is to assist students and staff in finding relevant books from the campus library catalogue "
        "and explaining borrowing policies.\n\n"
        "STRICT GROUNDING RULES:\n"
        "1. You must ONLY recommend books that exist in the PROVIDED CATALOGUE LIST below. "
        "Do NOT invent, hallucinate, or recommend external books that are not in this list.\n"
        "2. State the actual author, category, shelf location, and availability as listed.\n"
        "3. If a requested subject or title is not in the catalogue, explicitly state that our campus collection "
        "does not currently have it, and suggest the closest available book from our list.\n"
        "4. Standard library rules: Loan period is {loan_days} days, fine is {fine} BDT/day after due date, "
        "max active loans is {max_loans} books.\n"
        "5. Keep responses concise, warm, academic, and well-formatted with markdown bullet points.\n"
        "6. Do not mention API keys, database internals, or passwords under any circumstances."
    ).format(
        loan_days=lib_settings.loan_period_days,
        fine=lib_settings.fine_per_day,
        max_loans=lib_settings.max_active_loans
    )

    prompt_content = (
        f"{system_instruction}\n\n"
        f"--- OFFICIAL CAMPUS LIBRARY CATALOGUE (SOURCE OF TRUTH) ---\n"
        f"{catalog_context}\n"
        f"--- END OF CATALOGUE ---\n\n"
        f"User Query: {sanitized_query}\n"
        f"Response (Grounding strictly in the catalogue):"
    )

    url = f"{GEMINI_API_URL_TEMPLATE.format(model=model)}?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_content}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 600,
            "topP": 0.8
        }
    }

    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)

            candidates = res_json.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                reply_text = "".join(p.get('text', '') for p in parts).strip()
            else:
                reply_text = "I could not find an exact match for that query in our library database."

            # Verify and attach actual database book objects
            matched_books = match_books_in_text(reply_text, book_list)

            return {
                'reply': reply_text,
                'books': matched_books,
                'quick_chips': ["Search Algorithms", "Python programming", "Loan period rules", "Catalog"],
                'is_gemini': True,
                'ai_label': f"✦ AI-Generated by Gemini ({model}) · Grounded in Campus Database"
            }

    except urllib.error.HTTPError as e:
        status = e.code
        logger.warning("Gemini API HTTP Error %s: %s", status, e.reason)
        if status == 429:
            reason_msg = "Google Gemini free-tier quota is currently busy. Showing catalogue search results:"
        elif status in (400, 401, 403):
            reason_msg = "Gemini API key is invalid or restricted. Showing catalogue search results:"
        else:
            reason_msg = f"Gemini API returned status {status}. Showing catalogue search results:"
        return fallback_local_search(sanitized_query, reason=reason_msg)

    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning("Gemini API connection error: %s", str(e))
        return fallback_local_search(
            sanitized_query,
            reason="Gemini service timed out or is temporarily unreachable. Showing catalogue search results:"
        )

    except Exception as e:
        logger.error("Unexpected error in Gemini service: %s", str(e))
        return fallback_local_search(
            sanitized_query,
            reason="Library AI service encountered an error. Showing catalogue search results:"
        )
