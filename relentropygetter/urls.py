from django.urls import path
from gutenberg.views import books

urlpatterns = [
    path("books/", books),
]
