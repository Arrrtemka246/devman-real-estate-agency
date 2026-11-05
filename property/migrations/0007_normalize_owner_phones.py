import phonenumbers
from django.db import migrations


def normalize_phones(apps, schema_editor):
    Flat = apps.get_model("property", "Flat")
    alias = schema_editor.connection.alias
    batch = []
    for flat in Flat.objects.using(alias).all().iterator(chunk_size=1000):
        flat.owner_pure_phone = None
        try:
            phone = phonenumbers.parse(flat.owners_phonenumber, "RU")
        except phonenumbers.NumberParseException:
            phone = None
        if phone is not None and phonenumbers.is_valid_number(phone):
            flat.owner_pure_phone = phonenumbers.format_number(
                phone,
                phonenumbers.PhoneNumberFormat.E164,
            )
        batch.append(flat)
        if len(batch) == 1000:
            Flat.objects.using(alias).bulk_update(batch, ["owner_pure_phone"])
            batch = []
    if batch:
        Flat.objects.using(alias).bulk_update(batch, ["owner_pure_phone"])


class Migration(migrations.Migration):
    dependencies = [("property", "0006_complaints_likes_and_phone")]
    operations = [
        migrations.RunPython(normalize_phones, migrations.RunPython.noop),
    ]
