import importlib

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from .models import Complaint, Flat, Owner


class AgencyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="test_admin",
            password="local-test-password",
        )
        self.flat = Flat.objects.create(
            price=100,
            town="Таганрог",
            address="Садовая, 1",
            floor="1",
            rooms_number=2,
            active=True,
            construction_year=2016,
            new_building=True,
        )
        self.old_flat = Flat.objects.create(
            price=200,
            town="Москва",
            address="Лесная, 2",
            floor="2",
            rooms_number=1,
            active=True,
            construction_year=2000,
            new_building=False,
        )

    def test_catalog_filter_uses_editable_new_building_flag(self):
        response = self.client.get("/", {"new_building": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["flats"]), [self.flat])
        self.flat.new_building = False
        self.flat.save(update_fields=["new_building"])
        self.assertFalse(
            self.client.get(
                "/",
                {"new_building": "1"},
            ).context["flats"]
        )

    def test_admin_search_owners_and_inline_load_without_huge_selects(self):
        owner = Owner.objects.create(
            name="Иван Иванов",
            phonenumber="+79161234567",
        )
        owner.flats.add(self.flat)
        self.client.force_login(self.user)
        for query in ("Таганрог", "Садовая", "Иван"):
            response = self.client.get("/admin/property/flat/", {"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(list(response.context["cl"].result_list), [self.flat])
        response = self.client.get(f"/admin/property/flat/{self.flat.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("created_at", response.context["adminform"].form.fields)
        self.assertTrue(response.context["inline_admin_formsets"])
        self.assertEqual(admin.site._registry[Owner].raw_id_fields, ("flats",))

    def test_phone_validation_and_optional_phone(self):
        Owner(name="Без телефона").full_clean()
        with self.assertRaises(ValidationError):
            Owner(name="Ошибка", phonenumber="+70000000000").full_clean()
        Owner(name="Владелец", phonenumber="8 (916) 123-45-67").full_clean()

    def test_likes_complaints_and_multiple_ownership(self):
        self.flat.liked_by.add(self.user)
        self.flat.liked_by.add(self.user)
        self.assertEqual(self.flat.liked_by.count(), 1)
        complaint = Complaint.objects.create(
            flat=self.flat,
            user=self.user,
            text="Неправильная цена",
        )
        self.assertEqual(self.flat.complaints.get(), complaint)
        first = Owner.objects.create(name="Первый")
        second = Owner.objects.create(name="Второй")
        first.flats.add(self.flat, self.old_flat)
        second.flats.add(self.flat)
        self.assertEqual(self.flat.owned_by.count(), 2)
        self.assertEqual(first.flats.count(), 2)


class DataMigrationTests(TransactionTestCase):
    old_target = ("property", "0003_alter_flat_has_balcony")
    new_target = ("property", "0011_remove_legacy_owner_fields")

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.old_target])
        old_apps = executor.loader.project_state([self.old_target]).apps
        OldFlat = old_apps.get_model("property", "Flat")
        sources = [
            ("Один", "8 (916) 123-45-67", 2015),
            ("Один", "8 (916) 123-45-67", 2014),
            ("Другой", "+79161234567", None),
            ("Ошибка", "+70000000000", 2020),
            ("Текст", "нет телефона", 2001),
            ("Пусто", "", 2001),
        ]
        self.originals = {}
        for name, phone, year in sources:
            flat = OldFlat.objects.create(
                owner=name,
                owners_phonenumber=phone,
                price=123,
                town="Таганрог",
                address="Садовая",
                floor="1",
                rooms_number=2,
                active=True,
                construction_year=year,
            )
            self.originals[flat.pk] = (name, phone, year)
        executor = MigrationExecutor(connection)
        executor.migrate([self.new_target])

    def tearDown(self):
        MigrationExecutor(connection).migrate([self.new_target])
        super().tearDown()

    def test_every_original_contact_and_flat_survives(self):
        self.assertEqual(Flat.objects.count(), len(self.originals))
        self.assertEqual(Owner.objects.count(), 5)
        for pk, (name, phone, year) in self.originals.items():
            flat = Flat.objects.get(pk=pk)
            owner = flat.owned_by.get()
            self.assertEqual((owner.name, owner.source_phone), (name, phone))
            self.assertEqual(flat.new_building, year is not None and year >= 2015)
            if name in ("Ошибка", "Текст", "Пусто"):
                self.assertFalse(owner.phonenumber)
            else:
                self.assertEqual(str(owner.phonenumber), "+79161234567")

    def test_data_migrations_are_idempotent_and_rollback_keeps_contacts(self):
        target = ("property", "0010_link_owners")
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        apps = executor.loader.project_state([target]).apps
        old_owner = apps.get_model("property", "Owner")
        before = old_owner.objects.count()
        with connection.schema_editor() as editor:
            for filename, function in (
                ("0007_normalize_owner_phones", "normalize_phones"),
                ("0009_copy_owners", "copy_owners"),
                ("0010_link_owners", "link_owners"),
            ):
                module = importlib.import_module("property.migrations." + filename)
                getattr(module, function)(apps, editor)
        self.assertEqual(old_owner.objects.count(), before)
        self.assertEqual(old_owner.flats.through.objects.count(), len(self.originals))
        executor = MigrationExecutor(connection)
        executor.migrate([self.new_target])
        executor = MigrationExecutor(connection)
        executor.migrate([self.old_target])
        OldFlat = executor.loader.project_state([self.old_target]).apps.get_model(
            "property",
            "Flat",
        )
        actual = {
            flat.pk: (flat.owner, flat.owners_phonenumber, flat.construction_year)
            for flat in OldFlat.objects.all()
        }
        self.assertEqual(actual, self.originals)

    def test_rollback_refuses_to_lose_multiple_owners(self):
        flat = Flat.objects.first()
        Owner.objects.create(name="Второй собственник").flats.add(flat)
        with self.assertRaises(IrreversibleError):
            MigrationExecutor(connection).migrate(
                [
                    ("property", "0010_link_owners"),
                ]
            )
        self.assertEqual(flat.owned_by.count(), 2)
