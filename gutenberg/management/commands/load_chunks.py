import json

from django.db import connections
from django.core.management.base import BaseCommand

from gutenberg.models import Book, Chunk


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):

        with connections["keywordextractor"].cursor() as cursor:
            cursor.execute(
                'SELECT "gutenberg_chunk"."book_builder_id", "gutenberg_book"."gutenberg_id", "gutenberg_chunk"."text", "gutenberg_chunk"."vocab_counts", "gutenberg_chunk"."last_modified" FROM "gutenberg_chunk" INNER JOIN "gutenberg_book" ON ("gutenberg_chunk"."book_id" = "gutenberg_book"."id")'
            )
            keywordextractor_chunk_data = cursor.fetchall()

        chunks = []
        books = {}
        book_builder_ids = set()
        created_count = 0
        for (
            book_builder_id,
            book_gutenberg_id,
            text,
            vocab_counts,
            last_modified,
        ) in keywordextractor_chunk_data:
            book_builder_ids.add(book_builder_id)
            if book_gutenberg_id not in books:
                books[book_gutenberg_id] = Book.objects.get_or_create(
                    gutenberg_id=book_gutenberg_id
                )[0]

            if vocab_counts is not None:

                chunks.append(
                    Chunk(
                        book_builder_id=book_builder_id,
                        vocab_counts=json.loads(vocab_counts),
                        text=text,
                        book_id=books[book_gutenberg_id].id,
                        last_modified=last_modified,
                    )
                )

                if len(chunks) >= 2500:
                    Chunk.objects.bulk_create(
                        chunks, batch_size=250, ignore_conflicts=True
                    )
                    created_count += len(chunks)
                    print(f"{created_count} chunks scanned.")
                    chunks = []

        Chunk.objects.bulk_create(chunks, batch_size=250, ignore_conflicts=True)
        created_count += len(chunks)
        print(f"{created_count} chunks created.")

        deleted_count = 0
        delete_ids = []
        for book_builder_id in Chunk.objects.values_list("book_builder_id", flat=True):
            if book_builder_id not in book_builder_ids:
                delete_ids.append(book_builder_id)
                if len(delete_ids) >= 250:
                    count, _ = Chunk.objects.filter(id__in=delete_ids).delete()
                    deleted_count += count
                    delete_ids = []

        count, _ = Chunk.objects.filter(id__in=delete_ids).delete()
        deleted_count += count

        print(f"{deleted_count} chunks deleted.")
