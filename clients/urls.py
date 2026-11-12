from django.urls import path

from therapy.views import client_payments, client_reminders, client_sessions, complete_task

from .views import client_profile

urlpatterns = [
    path("", client_profile, name="client_profile"),
    path("sessions/", client_sessions, name="client_sessions"),
    path("payments/", client_payments, name="client_payments"),
    path("reminders/", client_reminders, name="client_reminders"),
    path("reminders/<int:task_id>/done/", complete_task, name="client_complete_task"),
]
