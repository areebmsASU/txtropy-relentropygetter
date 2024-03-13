import json

from django.db import connections
from django.core.management.base import BaseCommand

from gutenberg.models import Book


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):

        with connections["keywordextractor"].cursor() as cursor:
            cursor.execute(
                'SELECT "gutenberg_chunk"."book_builder_id", "gutenberg_chunk"."book_gutenberg_id", "gutenberg_chunk"."vocab_counts", "gutenberg_chunk"."rel_i", "gutenberg_chunk"."text" FROM "gutenberg_chunk"'
            )
            bookbuilder_chunk_data = cursor.fetchall()

        books = {}
        for (
            book_builder_id,
            book_gutenberg_id,
            vocab_counts,
            rel_i,
            text,
        ) in bookbuilder_chunk_data:
            if book_gutenberg_id not in books:
                books[book_gutenberg_id] = Book.objects.get_or_create(
                    gutenberg_id=book_gutenberg_id
                )[0]

            books[book_gutenberg_id].chunks.create(
                book_builder_id=book_builder_id,
                vocab_counts=json.loads(vocab_counts),
                rel_i=rel_i,
                text=text,
            )
