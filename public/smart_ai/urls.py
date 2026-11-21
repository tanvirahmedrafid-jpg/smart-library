from django.urls import path
from smart_ai import views

app_name = 'smart_ai'

urlpatterns = [
    path('chat/', views.ai_chat_api, name='chat_api'),
    path('search-suggest/', views.live_search_suggest_api, name='search_suggest'),
]
