from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tarot_readings", "0012_interaction_id"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="interactionlog",
            new_name="tarot_readi_source_b7a7cf_idx",
            old_name="tarot_readi_source_9d6c9e_idx",
        ),
        migrations.RenameIndex(
            model_name="interactionlog",
            new_name="tarot_readi_user_id_2b2ecb_idx",
            old_name="tarot_readi_user_id_2d19f8_idx",
        ),
    ]
