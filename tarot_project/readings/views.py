from django.shortcuts import render
from django.views.generic import TemplateView, CreateView
from django.http import HttpResponse
from .models import Card, Reading, CardPosition
import random

class HomeView(TemplateView):
    template_name = 'readings/home.html'

class GetReadingView(CreateView):
    model = Reading
    template_name = 'readings/reading.html'
    fields = ['reading_type']

    def form_valid(self, form):
        reading = form.save()
        cards = list(Card.objects.all())
        num_cards = int(reading.reading_type)
        
        selected_cards = random.sample(cards, num_cards)
        
        for position, card in enumerate(selected_cards):
            CardPosition.objects.create(
                reading=reading,
                card=card,
                position=position,
                is_reversed=random.choice([True, False])
            )
        
        return render(self.request, 'readings/reading_result.html', {
            'reading': reading
        }) 