from django.contrib import admin
from catalog.models import Category, Book, BookCopy

class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 2
    fields = ('copy_code', 'status', 'condition')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'category', 'shelf_location', 'available_copies_count', 'is_featured')
    list_filter = ('category', 'is_featured', 'cover_theme')
    search_fields = ('title', 'author', 'isbn')
    inlines = [BookCopyInline]

@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ('copy_code', 'book', 'status', 'condition', 'added_date')
    list_filter = ('status', 'condition')
    search_fields = ('copy_code', 'book__title', 'book__isbn')
