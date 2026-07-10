from decimal import Decimal, InvalidOperation

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def normalize_legacy_prices(apps, schema_editor):
    Advertisement = apps.get_model('marketplace', 'Advertisement')
    for advertisement in Advertisement.objects.all().iterator():
        raw = advertisement.price
        if raw in (None, ''):
            advertisement.price = None
        else:
            cleaned = ''.join(character for character in str(raw).replace(',', '') if character.isdigit() or character in '.-')
            try:
                value = Decimal(cleaned)
                advertisement.price = format(value, 'f') if value >= 0 else None
            except (InvalidOperation, ValueError):
                advertisement.price = None
        advertisement.save(update_fields=['price'])


class Migration(migrations.Migration):
    dependencies = [
        ('marketplace', '0003_remove_advertisement_image_message_conversation_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(normalize_legacy_prices, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='advertisement',
            name='title',
            field=models.CharField(max_length=180),
        ),
        migrations.AlterField(
            model_name='advertisement',
            name='description',
            field=models.TextField(max_length=5000),
        ),
        migrations.AlterField(
            model_name='advertisement',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='category',
            field=models.CharField(choices=[('books', 'Books and study materials'), ('electronics', 'Electronics'), ('fashion', 'Fashion'), ('services', 'Services'), ('accommodation', 'Accommodation'), ('food', 'Food'), ('other', 'Other')], default='other', max_length=30),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='condition',
            field=models.CharField(choices=[('new', 'New'), ('like_new', 'Like new'), ('used', 'Used'), ('not_applicable', 'Not applicable')], default='used', max_length=30),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='currency',
            field=models.CharField(default='NGN', max_length=3),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='location',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('reserved', 'Reserved'), ('sold', 'Sold'), ('archived', 'Archived')], default='active', max_length=20),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='views_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='advertisementimage',
            name='position',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='advertisement',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterModelOptions(
            name='advertisementimage',
            options={'ordering': ['position', 'id']},
        ),
        migrations.AlterField(
            model_name='message',
            name='advertisement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='legacy_messages', to='marketplace.advertisement'),
        ),
        migrations.AlterField(
            model_name='report',
            name='reporter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_reports', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='report',
            name='reason',
            field=models.TextField(max_length=1000),
        ),
        migrations.AlterModelOptions(
            name='report',
            options={'ordering': ['-reported_at']},
        ),
        migrations.CreateModel(
            name='SavedAdvertisement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('advertisement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='marketplace.advertisement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_advertisements', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='savedadvertisement',
            constraint=models.UniqueConstraint(fields=('user', 'advertisement'), name='unique_saved_advertisement'),
        ),
        migrations.AddConstraint(
            model_name='report',
            constraint=models.UniqueConstraint(fields=('reporter', 'advertisement'), name='unique_marketplace_report'),
        ),
        migrations.AddConstraint(
            model_name='advertisement',
            constraint=models.CheckConstraint(condition=models.Q(('price__gte', 0), ('price__isnull', True), _connector='OR'), name='marketplace_price_non_negative'),
        ),
        migrations.AddIndex(
            model_name='advertisement',
            index=models.Index(fields=['status', 'category', '-created_at'], name='marketplace_status_47559d_idx'),
        ),
        migrations.AddIndex(
            model_name='advertisement',
            index=models.Index(fields=['user', 'status', '-created_at'], name='marketplace_user_id_946ca8_idx'),
        ),
        migrations.AddIndex(
            model_name='advertisement',
            index=models.Index(fields=['price'], name='marketplace_price_c7360b_idx'),
        ),
    ]
