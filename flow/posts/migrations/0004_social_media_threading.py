from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_comment_threads(apps, schema_editor):
    Comment = apps.get_model('posts', 'Comment')
    top_level = Comment.objects.filter(parent__isnull=True)
    for comment in top_level.iterator():
        Comment.objects.filter(pk=comment.pk).update(root_id=comment.pk, depth=0)

    unresolved = Comment.objects.filter(parent__isnull=False).order_by('created_at')
    for comment in unresolved.iterator():
        parent = Comment.objects.filter(pk=comment.parent_id).first()
        if parent:
            root_id = parent.root_id or parent.id
            Comment.objects.filter(pk=comment.pk).update(root_id=root_id, depth=(parent.depth or 0) + 1)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('posts', '0003_comment_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hashtag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=80, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='post',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='post',
            name='hashtags',
            field=models.ManyToManyField(blank=True, related_name='posts', to='posts.hashtag'),
        ),
        migrations.AddField(
            model_name='post',
            name='mentioned_users',
            field=models.ManyToManyField(blank=True, related_name='mentioned_in_posts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='depth',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='comment',
            name='mentioned_users',
            field=models.ManyToManyField(blank=True, related_name='mentioned_in_comments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='root',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='thread_comments', to='posts.comment'),
        ),
        migrations.CreateModel(
            name='PostMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], max_length=12)),
                ('url', models.URLField(max_length=1200)),
                ('thumbnail_url', models.URLField(blank=True, max_length=1200)),
                ('public_id', models.CharField(blank=True, max_length=500)),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=120)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('duration_seconds', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('trim_start_seconds', models.DecimalField(decimal_places=3, default=0, max_digits=8)),
                ('trim_end_seconds', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('position', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='posts.post')),
            ],
            options={'ordering': ['position', 'id']},
        ),
        migrations.RunPython(backfill_comment_threads, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['post', 'parent', 'created_at'], name='comment_parent_time_idx'),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['root', 'created_at'], name='comment_thread_time_idx'),
        ),
        migrations.AddIndex(
            model_name='postmedia',
            index=models.Index(fields=['post', 'position'], name='post_media_order_idx'),
        ),
    ]
