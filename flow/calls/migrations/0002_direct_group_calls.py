from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0001_initial'),
        ('messaging', '0002_message_lifecycle_receipts'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='call_type',
            field=models.CharField(choices=[('audio', 'Audio'), ('video', 'Video')], default='video', max_length=10),
        ),
        migrations.AddField(
            model_name='room',
            name='conversation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='call_rooms', to='messaging.conversation'),
        ),
        migrations.AddField(
            model_name='room',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_call_rooms', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='room',
            name='ended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='room',
            name='started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='room',
            name='status',
            field=models.CharField(choices=[('ringing', 'Ringing'), ('active', 'Active'), ('ended', 'Ended'), ('rejected', 'Rejected'), ('missed', 'Missed')], default='active', max_length=12),
        ),
        migrations.AlterField(
            model_name='room',
            name='room_name',
            field=models.CharField(default=uuid.uuid4, max_length=100, unique=True),
        ),
        migrations.CreateModel(
            name='CallInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ringing', 'Ringing'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('left', 'Left')], default='ringing', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_call_invitations', to=settings.AUTH_USER_MODEL)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='calls.room')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='call_invitations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='room',
            index=models.Index(fields=['status', 'created_at'], name='call_room_status_idx'),
        ),
        migrations.AddIndex(
            model_name='room',
            index=models.Index(fields=['created_by', 'created_at'], name='call_room_creator_idx'),
        ),
        migrations.AddConstraint(
            model_name='callinvitation',
            constraint=models.UniqueConstraint(fields=('room', 'user'), name='unique_call_room_invitee'),
        ),
        migrations.AddIndex(
            model_name='callinvitation',
            index=models.Index(fields=['user', 'status', 'created_at'], name='call_invitee_status_idx'),
        ),
    ]
