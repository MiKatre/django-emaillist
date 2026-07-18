from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("emaillist", "0002_subscription_is_confirmed_subscription_subscribed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
