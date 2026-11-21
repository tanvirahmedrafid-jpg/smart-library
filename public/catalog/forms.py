from django import forms
from catalog.models import Book, Category

class BookForm(forms.ModelForm):
    initial_copies = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=3,
        required=False,
        label="Number of physical copies to add",
        widget=forms.NumberInput(attrs={'class': 'input', 'placeholder': 'e.g. 3'})
    )

    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'category', 'publisher', 'edition', 'shelf_location', 'description', 'cover_theme', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Book Title'}),
            'author': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Author Name(s)'}),
            'isbn': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. 978-0132350884'}),
            'category': forms.Select(attrs={'class': 'input'}),
            'publisher': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Publisher'}),
            'edition': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. 2nd Edition'}),
            'shelf_location': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Rack A-1, Shelf 3'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 3, 'placeholder': 'Brief description'}),
            'cover_theme': forms.Select(attrs={'class': 'input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'input-check'}),
        }
