from django.contrib.auth.forms import UserCreationForm
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView


class SignUpView(SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")
    success_message = "Аккаунт «%(username)s» создан. Теперь войдите в систему."
