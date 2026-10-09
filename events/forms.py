from django import forms

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = (
            "title",
            "slug",
            "summary",
            "description",
            "poster",
            "starts_at",
            "is_published",
        )
        labels = {
            "title": "Название",
            "slug": "URL-идентификатор",
            "summary": "Краткое описание",
            "description": "Описание",
            "poster": "Изображение",
            "starts_at": "Дата и время проведения",
            "is_published": "Опубликовано",
        }
        error_messages = {
            "title": {"required": "Укажите название события."},
            "slug": {
                "required": "Укажите URL-идентификатор события.",
                "unique": "Событие с таким URL-идентификатором уже существует.",
            },
            "summary": {"required": "Укажите краткое описание события."},
            "description": {"required": "Добавьте описание события."},
            "starts_at": {
                "required": "Укажите дату и время проведения.",
                "invalid": "Введите корректную дату и время.",
            },
        }
        widgets = {
            "starts_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
        }
