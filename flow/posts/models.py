from django.conf import settings
from django.db import models


class Hashtag(models.Model):
    name = models.CharField(max_length=80, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = (self.name or '').strip().lower().lstrip('#')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'#{self.name}'


class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reposted_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='reposts')
    hashtags = models.ManyToManyField(Hashtag, related_name='posts', blank=True)
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='mentioned_in_posts',
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post by {self.user.user_name or self.user.email} on {self.created_at}'

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def reposts_count(self):
        return self.reposts.count()


class PostMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'

    post = models.ForeignKey(Post, related_name='media', on_delete=models.CASCADE)
    media_type = models.CharField(max_length=12, choices=MediaType.choices)
    url = models.URLField(max_length=1200)
    thumbnail_url = models.URLField(max_length=1200, blank=True)
    public_id = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    trim_start_seconds = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    trim_end_seconds = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'id']
        indexes = [models.Index(fields=['post', 'position'], name='post_media_order_idx')]

    def __str__(self):
        return f'{self.media_type} for post {self.post_id}'


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_post_like_per_user'),
        ]

    def __str__(self):
        return f'Like by {self.user.user_name or self.user.email} on post {self.post.id}'


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    root = models.ForeignKey('self', null=True, blank=True, related_name='thread_comments', on_delete=models.CASCADE)
    depth = models.PositiveIntegerField(default=0)
    content = models.TextField()
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='mentioned_in_comments',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'parent', 'created_at'], name='comment_parent_time_idx'),
            models.Index(fields=['root', 'created_at'], name='comment_thread_time_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.parent_id:
            self.post_id = self.parent.post_id
            self.root_id = self.parent.root_id or self.parent_id
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0
        super().save(*args, **kwargs)
        if not self.parent_id and self.root_id != self.id:
            type(self).objects.filter(pk=self.pk).update(root_id=self.pk)
            self.root_id = self.pk

    def __str__(self):
        return f'Comment by {self.user.user_name or self.user.email} on post {self.post.id}'

    @property
    def replies_count(self):
        return self.thread_comments.exclude(pk=self.pk).count() if self.root_id == self.id else self.replies.count()


class Report(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='reports', on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report by {self.user.user_name or self.user.email} on post {self.post.id}'
