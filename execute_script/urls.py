"""execute_script URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from . import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('', views.automation_historicalAnalysis),
    path('admin/', admin.site.urls),
    path('historicalAnalysis/', views.automation_historicalAnalysis,name='historicalAnalysis'),
    path('monitoring/', views.automation_monitoring, name='monitong'),
    path('processMining/', views.automation_processMining, name='processtMining'),
    path('executeScript/', views.executeScript_restartJob),
    path('stopExtraction/', views.stopExtraction),
    path('executeScript_processMining/', views.executeScript_processMining),
    

]

urlpatterns += staticfiles_urlpatterns()
