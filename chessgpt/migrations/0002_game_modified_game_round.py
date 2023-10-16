# Generated by Django 4.2.6 on 2023-10-06 06:42

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chessgpt', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='game',
            name='round',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
