from django.shortcuts import render
from subprocess import run
import sys
from django.views.decorators.csrf import csrf_exempt
import json
from django.template import loader


# Create your views here.
from django.http import HttpResponse


@csrf_exempt


def automation_historicalAnalysis(request):
    return render((request),"ProcessMiningExtractors.html")
