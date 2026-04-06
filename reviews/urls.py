from django.urls import path
from . import views

urlpatterns = [
    path('like/<int:review_id>/', views.like_review, name='like_review'),
]