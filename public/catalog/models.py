from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='bi-book', help_text='Bootstrap or generic icon class')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Book(models.Model):
    COLOR_THEMES = [
        ('cover-orange', 'Smart Electric Orange'),
        ('cover-blue', 'Royal Navy Blue'),
        ('cover-sage', 'Emerald Sage'),
        ('cover-purple', 'Deep Indigo'),
        ('cover-rose', 'Crimson Coral'),
        ('cover-sand', 'Golden Amber'),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=30, unique=True, verbose_name="ISBN")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='books')
    publisher = models.CharField(max_length=150, blank=True)
    edition = models.CharField(max_length=50, blank=True, default='1st Edition')
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    shelf_location = models.CharField(max_length=100, help_text="e.g. Rack A-3, Shelf 2")
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    cover_theme = models.CharField(max_length=30, choices=COLOR_THEMES, default='cover-blue')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'title']

    def __str__(self):
        return f"{self.title} by {self.author}"

    @property
    def total_copies_count(self):
        return self.copies.exclude(status='archived').count()

    @property
    def available_copies_count(self):
        return self.copies.filter(status='available').count()

    @property
    def is_available(self):
        return self.available_copies_count > 0

    @property
    def price(self):
        return 450

    @property
    def replacement_price(self):
        return 450

    @property
    def available_copies(self):
        return self.copies.filter(status='available')

class BookCopy(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('issued', 'Issued'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Maintenance'),
        ('archived', 'Archived'),
    ]
    CONDITION_CHOICES = [
        ('new', 'Brand New'),
        ('good', 'Good Condition'),
        ('worn', 'Slightly Worn'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    copy_code = models.CharField(max_length=50, unique=True, help_text="Unique barcode or identifier, e.g. DIU-SE-101-C1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    added_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Book copies'
        ordering = ['copy_code']

    def __str__(self):
        return f"{self.book.title} [Copy: {self.copy_code}] - {self.get_status_display()}"

    @property
    def is_available(self):
        return self.status == 'available'
