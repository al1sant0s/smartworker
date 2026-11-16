import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from management.models import City, Company, Estate

from .models import AvailabilitySheet, CheckList

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DuplicateSheetWarningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = Company.objects.create(name="Construtora", cnpj="12345678000195")
        city = City.objects.first()
        estate = Estate.objects.create(
            name="Residencial",
            company=company,
            cep="88015-200",
            street="Rua A",
            district="Centro",
            city=city,
            sales_start=date(2026, 1, 1),
            delivery_date=date(2028, 1, 1),
        )
        cls.checklist = CheckList.objects.create(
            estate=estate, reference_month=date(2026, 10, 1)
        )
        cls.user = get_user_model().objects.create_user(
            email="user@example.com", password="x"
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def upload(self, name, content):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("checklist:checklist_detail", args=[self.checklist.pk]),
            {"upload": "", "file": SimpleUploadedFile(name, content)},
        )
        return [(m.level_tag, str(m)) for m in get_messages(response.wsgi_request)]

    def test_warns_when_content_is_identical(self):
        self.upload("a.txt", b"same content")
        messages = self.upload("b.txt", b"same content")
        self.assertEqual(AvailabilitySheet.objects.count(), 2)
        self.assertIn("warning", [level for level, _ in messages])

    def test_no_warning_when_content_differs(self):
        self.upload("a.txt", b"one")
        messages = self.upload("b.txt", b"two")
        self.assertNotIn("warning", [level for level, _ in messages])
