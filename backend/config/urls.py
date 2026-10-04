from django.urls import path
from review import views

urlpatterns = [
    path("", views.index),
    path("api/session/", views.session),
    path("api/login/", views.SessionLoginView.as_view()),
    path("api/logout/", views.logout),
    path("api/examples/<str:filename>/", views.Example.as_view()),
    path("api/traces/", views.TraceList.as_view()),
    path("api/traces/<uuid:run_id>/", views.TraceDetail.as_view()),
    path("api/traces/<uuid:run_id>/preview/", views.Preview.as_view()),
    path("api/traces/<uuid:run_id>/revisions/", views.Revisions.as_view()),
    path("api/traces/<uuid:run_id>/complete-review/", views.CompleteReview.as_view()),
    path("api/traces/<uuid:run_id>/report/", views.Report.as_view()),
    path("api/traces/<uuid:run_id>/source/", views.Source.as_view()),
]
handler500 = "review.errors.server_error"
