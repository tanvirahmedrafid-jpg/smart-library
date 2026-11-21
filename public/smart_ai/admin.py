from django.contrib import admin
from smart_ai.models import SmartQueryLog, BookInteractionLog, SearchLog, SurveyResponse

@admin.register(SmartQueryLog)
class SmartQueryLogAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'user', 'created_at')
    search_fields = ('query_text', 'response_text')

@admin.register(BookInteractionLog)
class BookInteractionLogAdmin(admin.ModelAdmin):
    list_display = ('book', 'member', 'interaction_type', 'created_at')
    list_filter = ('interaction_type',)

@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ('query', 'matched_book', 'user', 'timestamp')
    search_fields = ('query', 'matched_book__title')

@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('student', 'preferred_category', 'unavailable_frequency', 'satisfaction_score', 'suggested_title', 'submitted_at')
    list_filter = ('unavailable_frequency', 'satisfaction_score', 'preferred_category')
    search_fields = ('student__name', 'suggested_title', 'unmet_subject')
