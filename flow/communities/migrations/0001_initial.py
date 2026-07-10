import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Community',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, validators=[django.core.validators.MinLengthValidator(3)])),
                ('slug', models.SlugField(blank=True, max_length=150, unique=True)),
                ('description', models.TextField(max_length=1500)),
                ('category', models.CharField(choices=[('course', 'Course'), ('interest', 'Interest'), ('project', 'Project'), ('club', 'Club')], default='interest', max_length=20)),
                ('visibility', models.CharField(choices=[('public', 'Public'), ('private', 'Private')], default='public', max_length=20)),
                ('course_code', models.CharField(blank=True, max_length=30)),
                ('cover_image', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_communities', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CommunityMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('moderator', 'Moderator'), ('member', 'Member')], default='member', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active')], default='active', max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='communities.community')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['joined_at']},
        ),
        migrations.CreateModel(
            name='CommunityPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(max_length=5000)),
                ('attachment_url', models.URLField(blank=True)),
                ('is_pinned', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_posts', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='communities.community')),
            ],
            options={'ordering': ['-is_pinned', '-created_at']},
        ),
        migrations.CreateModel(
            name='CommunityResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('description', models.TextField(blank=True, max_length=1000)),
                ('url', models.URLField()),
                ('is_pinned', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resources', to='communities.community')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_resources', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-is_pinned', '-created_at']},
        ),
        migrations.AddConstraint(
            model_name='communitymembership',
            constraint=models.UniqueConstraint(fields=('community', 'user'), name='unique_community_membership'),
        ),
        migrations.AddIndex(
            model_name='community',
            index=models.Index(fields=['visibility', 'is_active', '-created_at'], name='communities_visibil_3d61cc_idx'),
        ),
        migrations.AddIndex(
            model_name='community',
            index=models.Index(fields=['category', 'course_code'], name='communities_categor_a3dbad_idx'),
        ),
        migrations.AddIndex(
            model_name='communitymembership',
            index=models.Index(fields=['community', 'status', 'role'], name='communities_communi_b1130a_idx'),
        ),
        migrations.AddIndex(
            model_name='communitymembership',
            index=models.Index(fields=['user', 'status'], name='communities_user_id_d86418_idx'),
        ),
        migrations.AddIndex(
            model_name='communitypost',
            index=models.Index(fields=['community', '-created_at'], name='communities_communi_f7ca2a_idx'),
        ),
        migrations.AddIndex(
            model_name='communityresource',
            index=models.Index(fields=['community', '-created_at'], name='communities_communi_b7c8dc_idx'),
        ),
    ]
