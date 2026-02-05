# Generated migration for adding updated_at field to Message model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0006_typingstatus_alter_queuedmessage_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]