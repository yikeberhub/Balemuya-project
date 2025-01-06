# Generated by Django 5.1.4 on 2025-01-06 13:32

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_skill_remove_professional_skills_professional_skills'),
    ]

    operations = [
        migrations.CreateModel(
            name='Admin',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('admin_level', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Admin',
                'verbose_name_plural': 'Admins',
            },
            bases=('users.user',),
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
            options={
                'verbose_name': 'Permission',
                'verbose_name_plural': 'Permissions',
            },
        ),
        migrations.CreateModel(
            name='AdminLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.admin')),
            ],
            options={
                'verbose_name': 'Admin Log',
                'verbose_name_plural': 'Admin Logs',
            },
        ),
        migrations.AddField(
            model_name='admin',
            name='permissions',
            field=models.ManyToManyField(blank=True, related_name='admin_permissions', to='users.permission'),
        ),
    ]
