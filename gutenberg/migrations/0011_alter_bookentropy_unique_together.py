# Generated by Django 5.0.2 on 2024-04-26 02:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gutenberg', '0010_rename_last_modified_chunk_last_updated_book_entropy_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='bookentropy',
            unique_together={('book', 'related_book')},
        ),
    ]
