from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'pdf_processor'

urlpatterns = [
    path('', views.search_page, name='home'),
    path('search/', views.search_page, name='search'),
    path('api/search/', views.search_page, name='search-api'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='pdf_processor:login'), name='logout'),
]
