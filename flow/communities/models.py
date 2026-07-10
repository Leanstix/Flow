from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.text import slugify


class Community(models.Model):
    class Category(models.TextChoices):
        COURSE = 'course', 'Course'
        INTEREST = 'interest', 'Interest'
        PROJECT = 'project', 'Project'
        CLUB = 'club', 'Club'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='owned_communities',
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120, validators=[MinLengthValidator(3)])
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(max_length=1500)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.INTEREST)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    course_code = models.CharField(max_length=30, blank=True)
    cover_image = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visibility', 'is_active', '-created_at']),
            models.Index(fields=['category', 'course_code']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:120] or 'community'
            slug = base_slug
            suffix = 2
            while Community.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CommunityMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MODERATOR = 'moderator', 'Moderator'
        MEMBER = 'member', 'Member'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'

    community = models.ForeignKey(Community, related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='community_memberships', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['joined_at']
        constraints = [
            models.UniqueConstraint(fields=['community', 'user'], name='unique_community_membership'),
        ]
        indexes = [
            models.Index(fields=['community', 'status', 'role']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f'{self.user} in {self.community}'


class CommunityPost(models.Model):
    community = models.ForeignKey(Community, related_name='posts', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='community_posts', on_delete=models.CASCADE)
    content = models.TextField(max_length=5000)
    attachment_url = models.URLField(blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [models.Index(fields=['community', '-created_at'])]

    def __str__(self):
        return f'Post {self.pk} in {self.community}'


class CommunityResource(models.Model):
    community = models.ForeignKey(Community, related_name='resources', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='community_resources', on_delete=models.CASCADE)
    title = models.CharField(max_length=180)
    description = models.TextField(max_length=1000, blank=True)
    url = models.URLField()
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [models.Index(fields=['community', '-created_at'])]

    def __str__(self):
        return self.title
