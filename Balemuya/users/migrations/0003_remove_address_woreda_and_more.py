# Generated by Django 5.0 on 2025-01-11 18:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_professionalprofile_category'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='address',
            name='woreda',
        ),
        migrations.RemoveField(
            model_name='customerprofile',
            name='total_interactions',
        ),
        migrations.RemoveField(
            model_name='user',
            name='kebele_id_image',
        ),
        migrations.AddField(
            model_name='user',
            name='kebele_id_back_image',
            field=models.ImageField(blank=True, null=True, upload_to='kebele_id_images/back_images'),
        ),
        migrations.AddField(
            model_name='user',
            name='kebele_id_front_image',
            field=models.ImageField(blank=True, null=True, upload_to='kebele_id_images/front_images'),
        ),
        migrations.AlterField(
            model_name='address',
            name='country',
            field=models.CharField(default='ethiopia', max_length=100),
        ),
        migrations.AlterField(
            model_name='address',
            name='kebele',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='address',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name='address',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name='address',
            name='region',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='address',
            name='street',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
