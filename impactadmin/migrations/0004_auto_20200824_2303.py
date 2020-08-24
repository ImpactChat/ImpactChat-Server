# Generated by Django 3.1 on 2020-08-24 23:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('impactadmin', '0003_user_locale'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='locale',
            field=models.CharField(choices=[('en', 'English'), ('fr', 'French')], default='en', max_length=2),
        ),
    ]
