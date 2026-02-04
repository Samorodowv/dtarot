from django.db import migrations, models


def backfill_interaction_id(apps, schema_editor):
    InteractionLog = apps.get_model("tarot_readings", "InteractionLog")

    for log in InteractionLog.objects.all().iterator():
        if log.interaction_id:
            continue

        interaction_id = None

        if log.reading_id:
            interaction_id = f"reading:{log.reading_id}"
        elif log.user_identifier and log.user_identifier.startswith("reading:"):
            interaction_id = log.user_identifier
        else:
            metadata = log.metadata or {}
            reading_id = metadata.get("reading_id")
            if reading_id:
                interaction_id = f"reading:{reading_id}"

        if interaction_id:
            InteractionLog.objects.filter(pk=log.pk).update(interaction_id=interaction_id)


class Migration(migrations.Migration):

    dependencies = [
        ("tarot_readings", "0011_schedule_interaction_cleanup"),
    ]

    operations = [
        migrations.AddField(
            model_name="interactionlog",
            name="interaction_id",
            field=models.CharField(blank=True, db_index=True, max_length=128, default=""),
        ),
        migrations.RunPython(backfill_interaction_id, migrations.RunPython.noop),
    ]
