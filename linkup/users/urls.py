from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.public_profile, name='public_profile'),
    path('profile/<str:username>/message/', views.message_user, name='message_user'),
    path('profile/<str:username>/report/', views.report_user, name='report_user'),
    path('profile/<str:username>/block/', views.block_user, name='block_user'),
]
