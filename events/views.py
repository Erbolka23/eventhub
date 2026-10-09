from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import EventForm
from .models import Event


class HomeView(TemplateView):
    template_name = "events/home.html"


class EventListView(ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return Event.objects.filter(is_deleted=False)


class EventCreateView(SuccessMessageMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_message = "Событие «%(title)s» создано."

    def get_success_url(self):
        return reverse("events:event_detail", kwargs={"pk": self.object.pk})


class EventUpdateView(SuccessMessageMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_message = "Событие «%(title)s» обновлено."

    def get_queryset(self):
        return Event.objects.filter(is_deleted=False)

    def get_success_url(self):
        return reverse("events:event_detail", kwargs={"pk": self.object.pk})


class EventDeleteView(DeleteView):
    model = Event
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy("events:event_list")

    def get_queryset(self):
        return Event.objects.filter(is_deleted=False)

    def form_valid(self, form):
        self.object.is_deleted = True
        self.object.save(update_fields=["is_deleted"])
        messages.success(self.request, f"Событие «{self.object.title}» удалено.")
        return HttpResponseRedirect(self.get_success_url())


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.filter(is_deleted=False)
