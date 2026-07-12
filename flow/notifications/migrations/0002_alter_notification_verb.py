from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='verb',
            field=models.CharField(
                choices=[
                    ('message', 'Message'),
                    ('like', 'Like'),
                    ('comment', 'Comment'),
                    ('comment_reply', 'Comment reply'),
                    ('mention', 'Mention'),
                    ('repost', 'Repost'),
                    ('friend_request', 'Friend request'),
                    ('friend_accepted', 'Friend accepted'),
                    ('system', 'System'),
                ],
                default='system',
                max_length=32,
            ),
        ),
    ]
