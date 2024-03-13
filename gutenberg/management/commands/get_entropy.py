from time import sleep

from concurrent.futures import ThreadPoolExecutor, wait
from django.core.management.base import BaseCommand
from django.db.models import Value, CharField, F
from django.db.models.functions import Replace, Cast, Length
from scipy.stats import entropy

from gutenberg.models import Book, Chunk, Entropy


class EntropyGetter:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=None)
        self.executor_futures = []

    def get_chunk_entropy(self, chunk_id, other_gutenberg_id):
        chunk = Chunk.objects.get(id=chunk_id)

        related_chunk_qs = (
            Chunk.objects.exclude(vocab_counts=None)
            .filter(book__gutenberg_id=other_gutenberg_id)
            .filter(vocab_counts__has_any_keys=list(chunk.vocab_counts))
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
            shared_vocab = [
                vocab
                for vocab in chunk.vocab_counts.keys()
                if vocab in related_chunk.vocab_counts.keys()
            ]
            if len(shared_vocab) > 1:

                combined_vocab = sorted(
                    set(
                        list(chunk.vocab_counts.keys())
                        + list(related_chunk.vocab_counts.keys())
                    )
                )

                chunk_counts = [chunk.vocab_counts[vocab] for vocab in shared_vocab]
                related_chunk_counts = [
                    related_chunk.vocab_counts[vocab] for vocab in shared_vocab
                ]

                rel_entr = entropy(related_chunk_counts, chunk_counts)
                rel_entr_normed = entropy(
                    chunk_counts, chunk_counts, len(combined_vocab)
                )

                entropy_objs.append(
                    Entropy(
                        chunk=chunk,
                        related_chunk=related_chunk,
                        shared_vocab_count=len(shared_vocab),
                        combined_vocab_count=len(combined_vocab),
                        rel_entr=rel_entr,
                        rel_entr_normed=rel_entr_normed,
                        shared_count_x_rel_entr=len(shared_vocab) * rel_entr,
                        shared_count_x_rel_entr_normed=len(shared_vocab) * rel_entr,
                        combined_count_x_rel_entr=len(combined_vocab) * rel_entr_normed,
                        combined_count_x_rel_entr_normed=(
                            len(combined_vocab) * rel_entr_normed
                        ),
                    )
                )
        Entropy.objects.bulk_create(entropy_objs, batch_size=250)

    def get_book_entropy(self, this_gutenberg_id, other_gutenberg_id):
        this_book = Book.objects.get(gutenberg_id=this_gutenberg_id)
        for chunk_id in this_book.chunks.exclude(vocab_counts=None).values_list(
            "id", flat=True
        ):
            # self.get_chunk_entropy(chunk_id, other_gutenberg_id)
            self.executor_futures.append(
                self.executor.submit(
                    self.get_chunk_entropy, chunk_id, other_gutenberg_id
                )
            )
        self.print_execution_status()

    def print_execution_status(self):
        done, not_done = wait(self.executor_futures, return_when="FIRST_COMPLETED")
        while len(not_done):
            sleep(1)
            done, not_done = wait(self.executor_futures, return_when="FIRST_COMPLETED")
            print(
                f"{len(not_done)} of {(len(done) + len(not_done))} tasks ({int((100 * len(not_done)) / (len(done) + len(not_done)))}%) remaining."
            )
        self.executor_futures = []


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def handle(self, *args, **options):
        entropy_getter = EntropyGetter()
        entropy_getter.get_book_entropy(33310, 3300)
