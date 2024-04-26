from collections import Counter
from time import sleep

from celery import shared_task
from concurrent.futures import ThreadPoolExecutor, wait
from django.db.models import Value, CharField, F
from django.db.models.functions import Replace, Cast, Length
from scipy.spatial.distance import jensenshannon
from scipy.stats import entropy

from gutenberg.models import Book, Chunk, Entropy, BookEntropy


class EntropyGetter:
    def __init__(self, gutenberg_id, other_gutenberg_id) -> None:
        self.book = Book.objects.get(gutenberg_id=gutenberg_id)
        self.other_book = Book.objects.get(gutenberg_id=other_gutenberg_id)

    def get(self):
        executor = ThreadPoolExecutor(max_workers=None)
        executor_futures = []

        for chunk_id in self.book.chunks.exclude(vocab_counts=None).values_list("id", flat=True):
            executor_futures.append(executor.submit(self.get_chunk_entropy, chunk_id))
        done, not_done = wait(executor_futures, return_when="FIRST_COMPLETED")
        while len(not_done):
            sleep(3)
            done, not_done = wait(executor_futures, return_when="FIRST_COMPLETED")
            print(
                f"{len(not_done)} of {(len(done) + len(not_done))} tasks ({int((100 * len(not_done)) / (len(done) + len(not_done)))}%) remaining."
            )
        self.get_book_entropy()

    def get_book_entropy(self):
        vals = self.calculate_entropy_values(
            vocab_counts=self.get_vocab_counts(self.book),
            related_vocab_counts=self.get_vocab_counts(self.other_book),
        )

        BookEntropy.objects.create(
            book=self.book,
            related_book=self.other_book,
            entr_gained=vals["entr_gained"],
            entr_lost=vals["entr_lost"],
            shared_vocab_counts=vals["shared_vocab_counts"],
            shared_vocab_count=vals["shared_vocab_count"],
            shared_vocab_ratio=vals["shared_vocab_ratio"],
            jensen_shannon=vals["jensen_shannon"],
        )

        BookEntropy.objects.create(
            related_book=self.book,
            book=self.other_book,
            entr_gained=vals["entr_lost"],
            entr_lost=vals["entr_gained"],
            shared_vocab_counts=vals["shared_vocab_counts"],
            shared_vocab_count=vals["shared_vocab_count"],
            shared_vocab_ratio=vals["shared_vocab_ratio"],
            jensen_shannon=vals["jensen_shannon"],
        )

    def get_chunk_entropy(self, chunk_id):
        chunk = Chunk.objects.get(id=chunk_id)

        related_chunk_qs = (
            self.other_book.chunks.filter(vocab_counts__has_any_keys=list(chunk.vocab_counts))
            .annotate(vocab_counts_str=Cast("vocab_counts", output_field=CharField()))
            .annotate(
                num_keys=Length(F("vocab_counts_str"))
                - Length(
                    Replace(
                        "vocab_counts_str",
                        Value(":"),
                        Value(""),
                        output_field=CharField(),
                    )
                )
            )
            .filter(num_keys__gte=2)
        )

        entropy_objs = []
        for related_chunk in related_chunk_qs:
            vals = self.calculate_entropy_values(chunk.vocab_counts, related_chunk.vocab_counts)
            if vals:
                entropy_objs.append(
                    Entropy(
                        chunk=chunk,
                        related_chunk=related_chunk,
                        entr_gained=vals["entr_gained"],
                        entr_lost=vals["entr_lost"],
                        shared_vocab_counts=vals["shared_vocab_counts"],
                        shared_vocab_count=vals["shared_vocab_count"],
                        shared_vocab_ratio=vals["shared_vocab_ratio"],
                        jensen_shannon=vals["jensen_shannon"],
                    )
                )

                entropy_objs.append(
                    Entropy(
                        related_chunk=chunk,
                        chunk=related_chunk,
                        entr_gained=vals["entr_lost"],
                        entr_lost=vals["entr_gained"],
                        shared_vocab_counts=vals["shared_vocab_counts"],
                        shared_vocab_count=vals["shared_vocab_count"],
                        shared_vocab_ratio=vals["shared_vocab_ratio"],
                        jensen_shannon=vals["jensen_shannon"],
                    )
                )

        Entropy.objects.bulk_create(entropy_objs, batch_size=250, ignore_conflicts=True)

    @staticmethod
    def get_vocab_counts(book):
        update_fields = []
        if not book.vocab_counts:
            book.vocab_counts = dict(
                sum(
                    [
                        Counter(vocab_counts)
                        for vocab_counts in book.chunks.exclude(
                            vocab_counts__isnull=True
                        ).values_list("vocab_counts", flat=True)
                    ],
                    Counter(),
                )
            )
            update_fields.append("vocab_counts")

        if not book.entropy:
            book.entropy = entropy(list(book.vocab_counts.values()))
            update_fields.append("entropy")
        if update_fields:
            book.save(update_fields=update_fields)
        return book.vocab_counts

    @staticmethod
    def calculate_entropy_values(vocab_counts, related_vocab_counts, min_shared_vocab=1):
        vals = {}
        shared_vocab = [
            vocab for vocab in vocab_counts.keys() if vocab in related_vocab_counts.keys()
        ]
        if len(shared_vocab) <= min_shared_vocab:
            return vals

        combined_vocab = sorted(set(list(vocab_counts.keys()) + list(related_vocab_counts.keys())))
        combined_vocab_count = sum(
            list(vocab_counts.values()) + list(related_vocab_counts.values())
        )
        chunk_counts_shared = [vocab_counts[vocab] for vocab in shared_vocab]
        related_chunk_counts_shared = [related_vocab_counts[vocab] for vocab in shared_vocab]

        vals["shared_vocab_counts"] = {
            vocab: (vocab_counts[vocab] + related_vocab_counts[vocab]) for vocab in shared_vocab
        }
        vals["shared_vocab_count"] = sum(vals["shared_vocab_counts"].values())
        vals["shared_vocab_ratio"] = vals["shared_vocab_count"] / combined_vocab_count

        vals["entr_gained"] = entropy(
            chunk_counts_shared, related_chunk_counts_shared, len(combined_vocab)
        )
        vals["entr_lost"] = entropy(
            related_chunk_counts_shared, chunk_counts_shared, len(combined_vocab)
        )
        vals["jensen_shannon"] = jensenshannon(
            [vocab_counts.get(vocab, 0) for vocab in combined_vocab],
            [related_vocab_counts.get(vocab, 0) for vocab in combined_vocab],
        )
        return vals


@shared_task
def get_similarity(gutenberg_id, other_gutenberg_id):
    EntropyGetter(gutenberg_id, other_gutenberg_id).get()


@shared_task
def bulk_get_similarity(gutenberg_id, other_gutenberg_ids):
    for other_gutenberg_id in other_gutenberg_ids:
        EntropyGetter(gutenberg_id, other_gutenberg_id).get()
