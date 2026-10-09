from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.messages import get_messages

from .models import Event


class EventCrudTests(TestCase):
    def setUp(self):
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
