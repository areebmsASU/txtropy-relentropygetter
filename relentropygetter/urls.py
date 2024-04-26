from django.urls import path
from gutenberg.views import books, get_related, get_similarity

urlpatterns = [
    path("books/", books),
    path("relations/", get_related),
    path("get_similarity/", get_similarity),
]
