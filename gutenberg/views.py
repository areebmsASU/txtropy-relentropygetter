import requests
from celery import shared_task
from django.http import JsonResponse

from gutenberg.models import Book, Chunk

KEYWORDEXTRACTOR_URL = "http://api.keywordextractor.txtropy.com"


@shared_task
def load_chunks(gutenberg_id):

    book = Book.objects.get(gutenberg_id=gutenberg_id)

    data = requests.get(f"{KEYWORDEXTRACTOR_URL}/chunks/{gutenberg_id}/").json()

    created_ids = []
    while data["chunks"]:
        chunks = []
        for chunk in data["chunks"]:
            chunks.append(
                Chunk(
                    book_builder_id=chunk["id"],
                    text=chunk["text"],
                    vocab_counts=chunk["vocab_counts"],
                    last_modified=chunk["last_modified"],
                    book_id=book.id,
                )
            )
            created_ids.append(chunk["id"])
        Chunk.objects.bulk_create(chunks)
        if "next_page" in data:
            data = requests.get(data["next_page"]).json()
        else:
            break

    book.chunks.exclude(book_builder_id__in=created_ids).delete()


def books(request):
    if request.method == "POST":
        try:
            book = Book.objects.filter(gutenberg_id=request.POST["id"]).first()
            if book is None:
                Book.objects.create(
                    gutenberg_id=request.POST["id"],
                    title=request.POST["title"],
                    author=request.POST["author"],
                )[1]
                status = "created"
            elif book.title == request.POST["title"] and book.author == request.POST["author"]:
                status = "ignored"
            else:
                book.title = request.POST["title"]
                book.author = request.POST["author"]
                book.save(update_fields=["title", "author"])
                status = "updated"

        except Exception as e:

            return JsonResponse({"error": repr(e)}, status=400)
        load_chunks.delay(gutenberg_id=book.gutenberg_id)
        return JsonResponse({"status": status})
