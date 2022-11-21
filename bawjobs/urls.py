from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('delete/<int:id>', views.delete, name='delete'),
    path('edit/<int:id>', views.edit, name='edit'),
    path('edit/savejob/<int:id>', views.savejob, name='savejob'),
    path('initextraction/<int:id>', views.initextraction, name='initextraction'),
    path('initextraction/startextraction/<int:id>', views.startextraction, name='startextraction'),
    path('initextraction/stopextraction/<int:id>', views.stopextraction, name='stopextraction'),
    path('initextraction/extractioncomplete/<int:id>', views.extractioncomplete, name='extractioncomplete'),
    path('createjob/', views.createjob, name='createjob'),
    path('createjob/addjob/', views.addjob, name='addjob'),
    path('copy/<int:id>', views.copy, name='copy'),
    path('copy/addjob/', views.addjob, name='addjob'),
    path('loadjsonfile/', views.loadjsonfile, name='loadjsonfile'),
    path('loadjsonfile/recordjsonfile/', views.recordjsonfile, name='recordjsonfile'),

]