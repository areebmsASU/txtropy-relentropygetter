from django.db import models

# Create your models here.


class Book(models.Model):
    gutenberg_id = models.IntegerField(unique=True)
    title = models.TextField()
    author = models.TextField()


class Chunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chunks")
    book_builder_id = models.IntegerField(unique=True)
    vocab_counts = models.JSONField(null=True)
    last_modified = models.DateTimeField()
    text = models.TextField()


class Entropy(models.Model):
    chunk = models.ForeignKey(Chunk, on_delete=models.CASCADE, related_name="entropies")
    related_chunk = models.ForeignKey(Chunk, on_delete=models.CASCADE, related_name="+")
    shared_vocab_counts = models.JSONField()
    shared_vocab_ratio = models.FloatField()
    shared_vocab_count = models.IntegerField()
    entr_gained = models.FloatField()
    entr_lost = models.FloatField()
    jensen_shannon = models.FloatField()

    class Meta:
        unique_together = [
            ["chunk", "related_chunk"],
        ]

    def __str__(self) -> str:
        return f"{self.chunk_id} --{self.entr_gained}--> {self.related_chunk_id}"
