from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class NavigationMenuTests(TestCase):
    def test_anonymous_user_sees_login_and_signup_links(self):
        response = self.client.get(reverse("events:home"))

        self.assertContains(response, reverse("events:event_list"))
        self.assertContains(response, reverse("events:event_create"))
        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, f'href="{reverse("signup")}"')
        self.assertNotContains(response, "Logout")

    def test_authenticated_user_sees_username_and_logout_form(self):
        user = User.objects.create_user(username="alice", password="StrongPass-123")
        self.client.force_login(user)

        response = self.client.get(reverse("events:event_list"))

        self.assertContains(response, "alice")
        self.assertContains(response, f'<form method="post" action="{reverse("logout")}"')
        self.assertContains(response, ">Logout</button>")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertNotContains(response, f'href="{reverse("login")}"')
        self.assertNotContains(response, f'href="{reverse("signup")}"')


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="StrongPass-123")

    def test_login_page_renders_form(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, reverse("signup"))

    def test_login_with_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("login"), {"username": "bob", "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertContains(response, "form-errors")
        self.assertContains(response, 'name="username"')
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_with_correct_password_authenticates_user(self):
        response = self.client.post(
            reverse("login"), {"username": "bob", "password": "StrongPass-123"}
        )

        self.assertRedirects(response, reverse("events:event_list"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_redirects_to_next_page(self):
        create_url = reverse("events:event_create")

        response = self.client.post(
            reverse("login"),
            {"username": "bob", "password": "StrongPass-123", "next": create_url},
        )

        self.assertRedirects(response, create_url)

    def test_logout_requires_post_and_logs_user_out(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse("logout"))
        self.assertEqual(get_response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

        post_response = self.client.post(reverse("logout"))
        self.assertRedirects(post_response, reverse("events:home"))
        self.assertNotIn("_auth_user_id", self.client.session)


class SignUpTests(TestCase):
    def test_signup_page_renders_form(self):
        response = self.client.get(reverse("signup"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_signup_creates_user_with_hashed_password(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "password1": "Complex-Pass-2026",
                "password2": "Complex-Pass-2026",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, "Complex-Pass-2026")
        self.assertTrue(user.check_password("Complex-Pass-2026"))

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "baduser",
                "password1": "Complex-Pass-2026",
                "password2": "Different-Pass-2026",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="baduser").exists())
