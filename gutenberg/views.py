import requests
from celery import shared_task
from django.db.models import Count, Avg, StdDev
from django.http import JsonResponse

from gutenberg.models import Book, Chunk, Entropy


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
                    last_updated=chunk["last_modified"],
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
    elif request.method == "GET":
        ids = []
        count = {}
        updated = {}
        for book in Book.objects.annotate(chunk_count=Count("chunks")).order_by("gutenberg_id"):
            ids.append(book.gutenberg_id)
            count[book.gutenberg_id] = book.chunk_count
            updated[book.gutenberg_id] = book.last_modified.date()
        return JsonResponse({"ids": ids, "count": count, "updated": updated})


def get_related(request):
    relations = []
    if request.method == "GET":
        ids = request.GET.get("chunks")
        if ids:
            mean, dev = Entropy.objects.aggregate(
                Avg("jensen_shannon"), StdDev("jensen_shannon")
            ).values()
            ids = list(map(int, ids.split(",")))
            chunk_ids = []
            for entropy_data in (
                Entropy.objects.filter(chunk__book_builder_id__in=ids)
                .order_by("jensen_shannon")
                .values(
                    "related_chunk__book__gutenberg_id",
                    "related_chunk__book__title",
                    "related_chunk__book__author",
                    "related_chunk__book_builder_id",
                    "related_chunk__text",
                    "shared_vocab_counts",
                    "entr_gained",
                    "entr_lost",
                    "jensen_shannon",
                )[:5]
            ):
                if entropy_data["related_chunk__book_builder_id"] not in chunk_ids:
                    chunk_ids.append(entropy_data["related_chunk__book_builder_id"])
                    relations.append(
                        {
                            "id": entropy_data["related_chunk__book_builder_id"],
                            "book": {
                                "id": entropy_data["related_chunk__book__gutenberg_id"],
                                "author": entropy_data["related_chunk__book__author"],
                                "title": entropy_data["related_chunk__book__title"],
                            },
                            "text": entropy_data["related_chunk__text"],
                            "entropy": {
                                "jensen_shannon": round(
                                    (entropy_data["jensen_shannon"] - mean) / dev, 4
                                ),
                                "gained": entropy_data["entr_gained"],
                                "lost": entropy_data["entr_lost"],
                            },
                            "shared_vocab": [
                                {"stem": stem, "count": count}
                                for stem, count in sorted(
                                    entropy_data["shared_vocab_counts"].items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )
                            ],
                        }
                    )
    return JsonResponse(relations, safe=False)
