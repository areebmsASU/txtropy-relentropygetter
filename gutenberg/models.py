from collections import Counter


from django.db import models

# Create your models here.


class Book(models.Model):
    gutenberg_id = models.IntegerField(unique=True)
    title = models.TextField()
    author = models.TextField()

    last_updated = models.DateTimeField()
    vocab_counts = models.JSONField(null=True)

    entropy = models.FloatField()


class BookEntropy(models.Model):
    date_calculated = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="entropies")
    related_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="+")
    shared_vocab_counts = models.JSONField()
    shared_vocab_ratio = models.FloatField()
    shared_vocab_count = models.IntegerField()
    entr_gained = models.FloatField()
    entr_lost = models.FloatField()
    jensen_shannon = models.FloatField()

    class Meta:
        unique_together = [
            ["book", "related_book"],
        ]


class Chunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chunks")
    book_builder_id = models.IntegerField(unique=True)
    last_updated = models.DateTimeField()
    text = models.TextField()

    vocab_counts = models.JSONField(null=True)
    entropy = models.FloatField()


class Entropy(models.Model):
    date_calculated = models.DateTimeField(auto_now_add=True)
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
