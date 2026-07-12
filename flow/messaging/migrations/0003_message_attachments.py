from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('messaging', '0002_message_lifecycle_receipts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name='MessageAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('image', 'Photo'), ('video', 'Video'), ('audio', 'Audio'), ('document', 'Document'), ('contact', 'Contact'), ('location', 'Location'), ('listing', 'Marketplace listing')], max_length=20)),
                ('url', models.URLField(blank=True, max_length=1200)),
                ('thumbnail_url', models.URLField(blank=True, max_length=1200)),
                ('public_id', models.CharField(blank=True, max_length=500)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=120)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('duration_seconds', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('position', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='messaging.message')),
            ],
            options={'ordering': ['position', 'id']},
        ),
        migrations.AddIndex(
            model_name='messageattachment',
            index=models.Index(fields=['message', 'position'], name='msg_attachment_order_idx'),
        ),
    ]
