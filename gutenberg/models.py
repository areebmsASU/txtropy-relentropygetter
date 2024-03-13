from django.db import models

# Create your models here.


class Book(models.Model):
    gutenberg_id = models.IntegerField(unique=True)


class Chunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chunks")
    book_builder_id = models.IntegerField(unique=True)
    vocab_counts = models.JSONField(null=True)
    rel_i = models.IntegerField()
    text = models.TextField()


class Entropy(models.Model):
    "the excess information from related_chunk (Q) when current information is chunk (P)"
    chunk = models.ForeignKey(Chunk, on_delete=models.CASCADE, related_name="entropies")
    related_chunk = models.ForeignKey(Chunk, on_delete=models.CASCADE, related_name="+")
    shared_vocab_count = models.IntegerField()
    combined_vocab_count = models.IntegerField()
    rel_entr = models.FloatField()
    rel_entr_normed = models.FloatField()
    shared_count_x_rel_entr = models.FloatField()
    shared_count_x_rel_entr_normed = models.FloatField()
    combined_count_x_rel_entr = models.FloatField()
    combined_count_x_rel_entr_normed = models.FloatField()

    class Meta:
        unique_together = [
            ["chunk", "related_chunk"],
        ]

    def __str__(self) -> str:
        return (
            f"{self.chunk_id} --{self.normalized_rel_entr}--> {self.related_chunk_id}"
        )
