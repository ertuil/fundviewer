# Generated by Django 4.2.3 on 2023-07-26 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fund', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='watchfund',
            name='fundname',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
