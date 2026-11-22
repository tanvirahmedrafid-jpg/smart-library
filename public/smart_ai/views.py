import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from catalog.models import Book
from library.services.gemini import ask_gemini_library_assistant
from smart_ai.models import SmartQueryLog

@csrf_exempt
@require_http_methods(["POST"])
def ai_chat_api(request):
    """
    Endpoint for S-liBro AI Assistant queries powered by Gemini / Database Grounding.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        message = data.get('message', '').strip()
    except Exception:
        message = request.POST.get('message', '').strip()

    result = ask_gemini_library_assistant(message, user=request.user)

    # Log query safely for library search analytics
    if message:
        try:
            auth_user = request.user if request.user.is_authenticated else None
            SmartQueryLog.objects.create(
                user=auth_user,
                query_text=message[:300],
                response_text=(result.get('reply', '')[:1000])
            )
        except Exception:
            pass

    return JsonResponse(result)

@require_http_methods(["GET"])
def live_search_suggest_api(request):
    """
    Real-time predictive search endpoint.
    Returns matched books with immediate copy availability.
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    matched_books = Book.objects.filter(
        title__icontains=query
    ) | Book.objects.filter(
        author__icontains=query
    ) | Book.objects.filter(
        isbn__icontains=query
    )
    
    results = []
    for b in matched_books.distinct()[:6]:
        results.append({
            'id': b.id,
            'title': b.title,
            'author': b.author,
            'category': b.category.name if b.category else 'General',
            'available': b.is_available,
            'available_count': b.available_copies_count,
            'shelf': b.shelf_location,
            'url': f"/books/{b.id}/"
        })

    return JsonResponse({'results': results})
