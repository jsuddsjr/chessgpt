# Generated by Django 4.2.5 on 2023-10-05 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chessgpt', '0003_alter_chathistory_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='chathistory',
            name='fname',
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='chathistory',
            name='role',
            field=models.CharField(choices=[('function', 'Function'), ('system', 'System'), ('user', 'User'), ('assistant', 'Assistant')], max_length=10),
        ),
    ]
