# Generated by Django 5.1.3 on 2024-12-09 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userauth', '0006_alter_user_interests'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='interests',
        ),
        migrations.AddField(
            model_name='user',
            name='interests',
            field=models.CharField(blank=True, max_length=225, null=True, verbose_name='Interest'),
        ),
    ]