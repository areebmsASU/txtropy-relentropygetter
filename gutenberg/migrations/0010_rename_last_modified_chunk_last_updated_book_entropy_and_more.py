# Generated by Django 5.0.2 on 2024-04-25 22:48

import datetime
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gutenberg", "0009_book_author_book_title"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chunk",
            old_name="last_modified",
            new_name="last_updated",
        ),
        migrations.AddField(
            model_name="book",
            name="entropy",
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="book",
            name="last_updated",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="book",
            name="vocab_counts",
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name="chunk",
            name="entropy",
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="entropy",
            name="date_calculated",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="BookEntropy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("date_calculated", models.DateTimeField(auto_now_add=True)),
                ("shared_vocab_counts", models.JSONField()),
                ("shared_vocab_ratio", models.FloatField()),
                ("shared_vocab_count", models.IntegerField()),
                ("entr_gained", models.FloatField()),
                ("entr_lost", models.FloatField()),
                ("jensen_shannon", models.FloatField()),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entropies",
                        to="gutenberg.book",
                    ),
                ),
                (
                    "related_book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="gutenberg.book",
                    ),
                ),
            ],
        ),
    ]
