# Generated manually for SavedJob model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saved_at', models.DateTimeField(auto_now_add=True, verbose_name='Saved at')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='jobs.job')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_jobs', to='users.user')),
            ],
            options={
                'ordering': ['-saved_at'],
                'unique_together': {('job', 'user')},
            },
        ),
    ]
