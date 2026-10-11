
from django import forms
from .models import ItemReport


class ItemReportForm(forms.ModelForm):

    class Meta:
        model = ItemReport

        fields = [
            'title',
            'category',
            'description',
            'location',
            'date_occurred',
            'image',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Black backpack',
            }),

            'category': forms.Select(),

            'description': forms.Textarea(attrs={
                'placeholder': 'Describe the item, including identifying details',
                'rows': 4,
            }),

            'location': forms.TextInput(attrs={
                'placeholder': 'e.g. Central Library, Room 204',
            }),

            'date_occurred': forms.DateInput(attrs={
                'type': 'date',
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                'Image size must be 5 MB or less.'
            )

        return image