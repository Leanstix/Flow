import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_receipts(apps, schema_editor):
    Message = apps.get_model('messaging', 'Message')
    MessageReceipt = apps.get_model('messaging', 'MessageReceipt')

    receipts = []
    for message in Message.objects.select_related('conversation').iterator():
        participant_ids = message.conversation.participants.exclude(id=message.sender_id).values_list('id', flat=True)
        for user_id in participant_ids:
            receipts.append(
                MessageReceipt(
                    message_id=message.id,
                    user_id=user_id,
                    delivered_at=message.timestamp if message.is_read else None,
                    read_at=message.timestamp if message.is_read else None,
                )
            )
        if len(receipts) >= 1000:
            MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)
            receipts = []
    if receipts:
        MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='messaging.message'),
        ),
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['timestamp']},
        ),
        migrations.CreateModel(
            name='MessageReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='messaging.message')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_receipts', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(backfill_receipts, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='messagereceipt',
            constraint=models.UniqueConstraint(fields=('message', 'user'), name='unique_message_receipt'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'timestamp'], name='msg_conversation_time_idx'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['sender', 'timestamp'], name='msg_sender_time_idx'),
        ),
        migrations.AddIndex(
            model_name='messagereceipt',
            index=models.Index(fields=['user', 'delivered_at'], name='receipt_user_delivery_idx'),
        ),
        migrations.AddIndex(
            model_name='messagereceipt',
            index=models.Index(fields=['user', 'read_at'], name='receipt_user_read_idx'),
        ),
    ]
