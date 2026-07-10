# Generated manually for realtime notification support

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('messaging', '0001_initial'),
        ('posts', '0003_comment_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('verb', models.CharField(choices=[('message', 'Message'), ('like', 'Like'), ('comment', 'Comment'), ('comment_reply', 'Comment reply'), ('repost', 'Repost'), ('friend_request', 'Friend request'), ('friend_accepted', 'Friend accepted'), ('system', 'System')], default='system', max_length=32)),
                ('message', models.TextField(blank=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actor_notifications', to=settings.AUTH_USER_MODEL)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('target_comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='posts.comment')),
                ('target_conversation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='messaging.conversation')),
                ('target_post', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='posts.post')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_read', '-created_at'], name='notificatio_recipie_90987d_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['verb', '-created_at'], name='notificatio_verb_91fa2b_idx'),
        ),
    ]
