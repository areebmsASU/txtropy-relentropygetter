from django.urls import path
from gutenberg.views import books, get_related

urlpatterns = [path("books/", books), path("relations/", get_related)]
