# Generated by Django 4.2.9 on 2024-01-23 12:29

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emaillist', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='is_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='subscription',
            name='subscribed_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
