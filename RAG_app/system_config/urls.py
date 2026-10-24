"""
URL configuration for GenAI project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from GenAI_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('add/', views.add_page, name='add_page'),
    path('add_task/', views.add_task, name='add_task'),
    path('update/', views.update_page, name='update_page'),
    path('update_status/', views.update_status, name='update_status')
    ,path('delete/<int:task_number>/', views.delete_task, name='delete_task')
    ,path('history/<int:task_number>/', views.task_history, name='task_history')
]
