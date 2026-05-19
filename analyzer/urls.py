from django.urls import path
from . import views

urlpatterns = [
    path("", views.intro, name="intro"),
    path("dashboard/", views.index, name="index"),
    path("profile/", views.profile_view, name="profile"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("report/<int:report_id>/", views.report_view, name="report"),
    path("api/analyze/", views.start_analysis, name="start_analysis"),
    path("api/status/<int:report_id>/", views.poll_status, name="poll_status"),
    path("api/competitors/add/", views.add_competitor, name="add_competitor"),
    path("api/competitors/delete/<int:comp_id>/", views.delete_competitor, name="delete_competitor"),
    path("download/<int:report_id>/", views.download_pptx, name="download_pptx"),
]
