from django import forms
from .models import Reading

class PromoCodeForm(forms.Form):
    promo_code = forms.CharField(
        required=True,
        label='Промокод',
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-700 text-white rounded-lg p-2',
            'placeholder': 'Введите промокод для мгновенного расклада'
        })
    )

class ReadingForm(forms.ModelForm):
    class Meta:
        model = Reading
        fields = ['user_age', 'user_gender', 'question']
        labels = {
            'user_age': 'Ваш возраст',
            'user_gender': 'Ваш пол',
            'question': 'Ваш вопрос',
        }
        widgets = {
            'user_age': forms.NumberInput(attrs={
                'class': 'w-full bg-gray-700 text-white rounded-lg p-2 mb-4',
                'placeholder': 'Введите ваш возраст'
            }),
            'user_gender': forms.Select(attrs={
                'class': 'w-full bg-gray-700 text-white rounded-lg p-2 mb-4'
            }),
            'question': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 text-white rounded-lg p-2 mb-4',
                'rows': 4,
                'placeholder': 'Введите ваш вопрос к картам'
            }),
        }

    def __init__(self, *args, promo_applied=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_gender'].empty_label = "-- Выберите пол --"
        self.fields['user_age'].required = True
        self.fields['user_gender'].required = True
        self.fields['question'].required = not promo_applied
        self.fields['question'].initial = " "  # Set default value as a space
        
        # Обновляем placeholder для поля вопроса в зависимости от статуса промокода
        if promo_applied:
            self.fields['question'].widget.attrs['placeholder'] = 'Можете оставить поле пустым для общего расклада'
        else:
            self.fields['question'].widget.attrs['placeholder'] = 'Введите ваш вопрос к картам'

    def clean_user_age(self):
        age = self.cleaned_data.get('user_age')
        if age is not None and (age < 18 or age > 100):
            raise forms.ValidationError('Возраст должен быть от 18 до 100 лет')
        return age 