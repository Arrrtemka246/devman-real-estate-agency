from django.db import migrations


def copy_owners(apps, schema_editor):
    Flat = apps.get_model("property", "Flat")
    Owner = apps.get_model("property", "Owner")
    alias = schema_editor.connection.alias
    contacts = (
        Flat.objects.using(alias)
        .values_list(
            "owner",
            "owner_pure_phone",
            "owners_phonenumber",
        )
        .distinct()
    )
    for name, phone, original_phone in contacts.iterator(chunk_size=1000):
        Owner.objects.using(alias).get_or_create(
            name=name,
            phonenumber=str(phone or ""),
            source_phone=original_phone,
        )


class Migration(migrations.Migration):
    dependencies = [("property", "0008_owner")]
    operations = [
        migrations.RunPython(copy_owners, migrations.RunPython.noop),
    ]
