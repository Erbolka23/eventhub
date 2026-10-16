import shutil
import tempfile
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from PIL import Image

from .models import Event


class EventCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="organizer", password="StrongPass-123"
        )
        self.client.force_login(self.user)
        self.event = Event.objects.create(
            title="Тестовое событие",
            slug="test-event",
            summary="Краткое описание",
            description="Описание события",
            starts_at="2026-11-01T12:30:00Z",
        )

    def test_event_list_displays_existing_event(self):
        response = self.client.get(reverse("events:event_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)

    def test_create_event(self):
        response = self.client.post(
            reverse("events:event_create"),
            {
                "title": "Новое событие",
                "slug": "new-event",
                "summary": "Краткое описание нового события",
                "description": "Подробное описание нового события",
                "starts_at": "2026-12-10T18:00",
                "is_published": "on",
            },
        )

        created_event = Event.objects.get(slug="new-event")
        self.assertRedirects(
            response,
            reverse("events:event_detail", kwargs={"pk": created_event.pk}),
        )
        self.assertEqual(Event.objects.count(), 2)

    def test_create_event_rejects_invalid_form(self):
        response = self.client.post(
            reverse("events:event_create"),
            {
                "title": "",
                "slug": "invalid-event",
                "summary": "Краткое описание",
                "description": "Описание события",
                "starts_at": "2026-12-10T18:00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Укажите название события.")
        self.assertFalse(Event.objects.filter(slug="invalid-event").exists())

    def test_update_event_changes_existing_record(self):
        response = self.client.post(
            reverse("events:event_update", kwargs={"pk": self.event.pk}),
            {
                "title": "Обновлённое событие",
                "slug": self.event.slug,
                "summary": self.event.summary,
                "description": "Обновлённое описание",
                "starts_at": "2026-11-02T12:30",
                "is_published": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("events:event_detail", kwargs={"pk": self.event.pk}),
        )
        self.assertEqual(Event.objects.count(), 1)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Обновлённое событие")
        self.assertEqual(self.event.description, "Обновлённое описание")

    def test_delete_requires_confirmation_and_soft_deletes_on_post(self):
        delete_url = reverse("events:event_delete", kwargs={"pk": self.event.pk})

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_deleted)

        response = self.client.post(delete_url)

        self.assertRedirects(response, reverse("events:event_list"))
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_deleted)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        self.assertTrue(
            any(
                "удалено" in message.message
                for message in get_messages(response.wsgi_request)
            )
        )

    def test_delete_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        delete_url = reverse("events:event_delete", kwargs={"pk": self.event.pk})

        response = client.post(delete_url)

        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_deleted)

    def test_soft_deleted_event_is_hidden_from_list_and_detail(self):
        detail_url = reverse("events:event_detail", kwargs={"pk": self.event.pk})
        update_url = reverse("events:event_update", kwargs={"pk": self.event.pk})
        self.event.is_deleted = True
        self.event.save()

        list_response = self.client.get(reverse("events:event_list"))
        detail_response = self.client.get(detail_url)
        update_response = self.client.get(update_url)

        self.assertNotContains(list_response, self.event.title)
        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)

    def test_edit_and_delete_urls_are_available(self):
        self.assertEqual(
            self.client.get(
                reverse("events:event_update", kwargs={"pk": self.event.pk})
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("events:event_delete", kwargs={"pk": self.event.pk})
            ).status_code,
            200,
        )


    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_authenticated_user_can_upload_poster(self):
        image = BytesIO()
        Image.new("RGB", (10, 10), "red").save(image, "PNG")
        poster = SimpleUploadedFile("poster.png", image.getvalue(), content_type="image/png")

        response = self.client.post(
            reverse("events:event_create"),
            {
                "title": "Событие с постером",
                "slug": "event-with-poster",
                "summary": "Краткое описание",
                "description": "Описание",
                "starts_at": "2026-12-10T18:00",
                "poster": poster,
            },
        )

        created_event = Event.objects.get(slug="event-with-poster")
        self.assertRedirects(
            response, reverse("events:event_detail", kwargs={"pk": created_event.pk})
        )
        self.assertTrue(created_event.poster.name.startswith("events/posters/"))
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

class EventAccessTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Открытое событие",
            slug="public-event",
            summary="Краткое описание",
            description="Описание события",
            starts_at="2026-11-01T12:30:00Z",
        )
        self.valid_data = {
            "title": "Анонимное событие",
            "slug": "anonymous-event",
            "summary": "Краткое описание",
            "description": "Описание",
            "starts_at": "2026-12-10T18:00",
        }

    def test_list_and_detail_are_public(self):
        self.assertEqual(self.client.get(reverse("events:event_list")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("events:event_detail", kwargs={"pk": self.event.pk})
            ).status_code,
            200,
        )

    def test_list_hides_soft_deleted_events(self):
        Event.objects.create(
            title="Скрытое событие",
            slug="hidden-event",
            summary="Краткое описание",
            description="Описание",
            starts_at="2026-11-02T12:30:00Z",
            is_deleted=True,
        )

        response = self.client.get(reverse("events:event_list"))

        self.assertContains(response, self.event.title)
        self.assertNotContains(response, "Скрытое событие")
        self.assertContains(
            response, reverse("events:event_detail", kwargs={"pk": self.event.pk})
        )

    def test_empty_list_shows_message(self):
        Event.objects.update(is_deleted=True)

        response = self.client.get(reverse("events:event_list"))

        self.assertContains(response, "Каталог пока пуст")

    def test_anonymous_user_is_redirected_from_create_page(self):
        create_url = reverse("events:event_create")

        get_response = self.client.get(create_url)
        post_response = self.client.post(create_url, self.valid_data)

        expected = f"{reverse('login')}?next={create_url}"
        self.assertRedirects(get_response, expected)
        self.assertRedirects(post_response, expected)
        self.assertFalse(Event.objects.filter(slug="anonymous-event").exists())

    def test_anonymous_user_cannot_update_or_delete(self):
        update_url = reverse("events:event_update", kwargs={"pk": self.event.pk})
        delete_url = reverse("events:event_delete", kwargs={"pk": self.event.pk})

        update_response = self.client.post(update_url, {**self.valid_data, "slug": "changed"})
        delete_response = self.client.post(delete_url)

        self.assertRedirects(update_response, f"{reverse('login')}?next={update_url}")
        self.assertRedirects(delete_response, f"{reverse('login')}?next={delete_url}")
        self.event.refresh_from_db()
        self.assertEqual(self.event.slug, "public-event")
        self.assertFalse(self.event.is_deleted)

    def test_anonymous_user_does_not_see_edit_and_delete_links(self):
        response = self.client.get(reverse("events:event_list"))

        self.assertNotContains(
            response, reverse("events:event_delete", kwargs={"pk": self.event.pk})
        )

