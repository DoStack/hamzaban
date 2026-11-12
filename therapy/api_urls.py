from django.urls import path

from therapy import api

urlpatterns = [
    path("me/", api.me, name="api_me"),
    path("login/", api.login_api, name="api_login"),
    path("logout/", api.logout_api, name="api_logout"),
    path("register/", api.register_api, name="api_register"),
    path("therapist-register/", api.therapist_register_api, name="api_therapist_register"),
    path("home/", api.home_api, name="api_home"),
    path("therapists/", api.therapists_api, name="api_therapists"),
    path("therapists/<uslug:slug>/", api.therapist_detail_api, name="api_therapist_detail"),
    path("book/<uslug:slug>/<int:slot_id>/", api.book_api, name="api_book"),
    path("client/home/", api.client_home_api, name="api_client_home"),
    path("client/account/", api.client_account_api, name="api_client_account"),
    path("client/sessions/", api.client_sessions_api, name="api_client_sessions"),
    path("client/payments/", api.client_payments_api, name="api_client_payments"),
    path("client/notifications/", api.client_notifications_api, name="api_client_notifications"),
    path("client/tasks/<int:task_id>/done/", api.client_task_done_api, name="api_client_task_done"),
    path("therapist/home/", api.therapist_home_api, name="api_therapist_home"),
    path("therapist/notifications/", api.therapist_notifications_api, name="api_therapist_notifications"),
    path("therapist/students/", api.therapist_students_api, name="api_therapist_students"),
    path("therapist/students/add/", api.therapist_add_student_api, name="api_therapist_add_student"),
    path("therapist/students/<int:user_id>/", api.therapist_crm_api, name="api_therapist_crm"),
    path("therapist/caseload/", api.therapist_caseload_api, name="api_therapist_caseload"),
    path("therapist/tasks/", api.therapist_tasks_api, name="api_therapist_tasks"),
    path("therapist/income/", api.therapist_income_api, name="api_therapist_income"),
    path("therapist/profile/", api.therapist_profile_api, name="api_therapist_profile"),
    path("therapist/hours/", api.therapist_hours_api, name="api_therapist_hours"),
    path("therapist/sessions/", api.therapist_sessions_api, name="api_therapist_sessions"),
]
