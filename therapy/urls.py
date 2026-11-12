from django.urls import path

from therapy.views import (
    add_student,
    caseload,
    crm,
    hours,
    income,
    profile_edit,
    students,
    tasks,
    therapist_home,
    therapist_notifications,
    therapist_sessions,
)

urlpatterns = [
    path("home/", therapist_home, name="therapist_home"),
    path("notifications/", therapist_notifications, name="therapist_notifications"),
    path("students/", students, name="therapist_students"),
    path("students/add/", add_student, name="therapist_add_student"),
    path("students/<int:user_id>/", crm, name="therapist_crm"),
    path("caseload/", caseload, name="therapist_caseload"),
    path("tasks/", tasks, name="therapist_tasks"),
    path("income/", income, name="therapist_income"),
    path("profile/", profile_edit, name="therapist_profile"),
    path("hours/", hours, name="therapist_hours"),
    path("sessions/", therapist_sessions, name="therapist_sessions"),
]
