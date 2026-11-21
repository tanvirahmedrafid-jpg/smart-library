from django.db import models
from django.contrib.auth.models import User
from catalog.models import Book, Category
from accounts.models import MemberProfile

class SmartQueryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query_text = models.CharField(max_length=300)
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AI Query: {self.query_text[:50]}"

class BookInteractionLog(models.Model):
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='interactions')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, default='view') # view, search, borrow
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class SearchLog(models.Model):
    query = models.CharField(max_length=255)
    matched_book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='search_hits')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Search: '{self.query}' at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class SurveyResponse(models.Model):
    UNAVAILABLE_FREQ_CHOICES = [
        ('never', 'Never'),
        ('rarely', 'Rarely'),
        ('sometimes', 'Sometimes'),
        ('often', 'Often'),
        ('very_often', 'Very Often'),
    ]

    student = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='surveys')
    preferred_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='survey_interests')
    unmet_subject = models.CharField(max_length=200, blank=True, help_text="Academic subjects lacking resources")
    unavailable_frequency = models.CharField(max_length=20, choices=UNAVAILABLE_FREQ_CHOICES, default='sometimes')
    satisfaction_score = models.PositiveSmallIntegerField(default=4, help_text="1 to 5 scale")
    wants_recommendations = models.BooleanField(default=True)
    suggested_title = models.CharField(max_length=255, blank=True, help_text="Specific book title or author requested to acquire")
    suggestions = models.TextField(blank=True, help_text="Other suggestions for library")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Survey by {self.student.name} ({self.submitted_at.strftime('%Y-%m-%d')})"
