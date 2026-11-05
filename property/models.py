from django.conf import settings
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Flat(models.Model):
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_flats",
        verbose_name="Кому понравилась квартира",
        blank=True,
    )
    created_at = models.DateTimeField(
        "Когда создано объявление", default=timezone.now, db_index=True
    )

    description = models.TextField("Текст объявления", blank=True)
    price = models.IntegerField("Цена квартиры", db_index=True)

    town = models.CharField(
        "Город, где находится квартира", max_length=50, db_index=True
    )
    town_district = models.CharField(
        "Район города, где находится квартира",
        max_length=50,
        blank=True,
        help_text="Чертаново Южное",
    )
    address = models.TextField(
        "Адрес квартиры", help_text="ул. Подольских курсантов д.5 кв.4"
    )
    floor = models.CharField(
        "Этаж", max_length=3, help_text="Первый этаж, последний этаж, пятый этаж"
    )

    rooms_number = models.IntegerField("Количество комнат в квартире", db_index=True)
    living_area = models.IntegerField(
        "количество жилых кв.метров", null=True, blank=True, db_index=True
    )

    has_balcony = models.BooleanField(
        "Наличие балкона", null=True, blank=True, db_index=True
    )
    new_building = models.BooleanField(
        "Новостройка",
        null=True,
        blank=True,
        db_index=True,
    )
    active = models.BooleanField("Активно-ли объявление", db_index=True)
    construction_year = models.IntegerField(
        "Год постройки здания", null=True, blank=True, db_index=True
    )

    def __str__(self):
        return f"{self.town}, {self.address} ({self.price}р.)"


class Complaint(models.Model):
    flat = models.ForeignKey(
        Flat,
        on_delete=models.CASCADE,
        related_name="complaints",
        verbose_name="Квартира",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="flat_complaints",
        verbose_name="Пользователь",
        null=True,
        blank=True,
    )
    text = models.TextField("Текст жалобы")
    created_at = models.DateTimeField("Дата жалобы", default=timezone.now)

    class Meta:
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"

    def __str__(self):
        return f"Жалоба №{self.pk} на квартиру №{self.flat_id}"


class Owner(models.Model):
    name = models.CharField("ФИО собственника", max_length=200)
    phonenumber = PhoneNumberField(
        "Телефон собственника",
        region="RU",
        blank=True,
        default="",
    )
    source_phone = models.CharField(
        "Исходная запись телефона",
        max_length=20,
        blank=True,
        default="",
        help_text="Сохранена при переносе данных, включая ошибочные номера.",
    )
    flats = models.ManyToManyField(
        Flat,
        related_name="owned_by",
        verbose_name="Квартиры",
        blank=True,
    )

    class Meta:
        verbose_name = "Собственник"
        verbose_name_plural = "Собственники"
        constraints = [
            models.UniqueConstraint(
                fields=("name", "phonenumber", "source_phone"),
                name="unique_owner_source_contact",
            ),
        ]

    def __str__(self):
        phone = self.phonenumber or self.source_phone
        return f"{self.name} ({phone})" if phone else self.name
