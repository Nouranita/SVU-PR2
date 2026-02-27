from django.urls import path
from .views import predict, health

urlpatterns = [
    path("predict/", predict, name="predict"),
    path("health/", health, name="health"),
]
