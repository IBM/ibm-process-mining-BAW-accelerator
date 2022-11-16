from django.db import models

# Create your models here.
from django.db import models

class Bawjobs(models.Model):
  job_name = models.CharField(max_length=255)
  root_url = models.CharField(max_length=255)
  project = models.CharField(max_length=255)
  process_name = models.CharField(max_length=255)
  ipm_url = models.CharField(max_length=255)
  ipm_project_key = models.CharField(max_length=255)
