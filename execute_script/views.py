from django.shortcuts import render
from subprocess import run
import sys
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.
from django.http import HttpResponse


@csrf_exempt

def format_config_parameters(config):
    
    # Add last / to the IPM url
    if (config['BAW']['root_url'][-1] != '/'):
        config['BAW']['root_url'] = config['BAW']['root_url'] + '/'

    # Remove last / from the IPM url
    if (config['IPM']['url'] != ""):
        if (config['IPM']['url'][-1] == '/') :
            config['IPM']['url'] = config['IPM']['url'][:-1]

    # add keys used to keep track of the latest run
    config['BAW']['last_after'] = ""
    config['BAW']['last_before'] = ""  


def automation_historicalAnalysis(request):
    return render((request),"automation_historicalAnalysis.html")

def automation_monitoring(request):
    return render((request),"automation_monitoring.html")

def automation_processMining(request):
    return render((request),"automation_processMining.html")

def executeScript_restartJob(request):
    # Script to restart a job
    body_unicode = request.body.decode('utf-8')
    body_json = json.loads(body_unicode)
    job_name = body_json['job_name']
    filename = "config/config_%s.json" % job_name

    # update the config file (set exit = 0) and change the update_rate and extraction_interval is set in the UI
    file = open(filename, 'r')
    config = json.load(file)
    config['JOB']['exit'] = 0
    config['JOB']['update_rate'] = body_json['update_rate']
    config['BAW']['extraction_interval'] = body_json['extraction_interval']
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()
    print("Resume execution with configuration file : %s" % filename)
    run([sys.executable,'BAW_to_IPM.py', filename], shell=False)
    return HttpResponse("-- executeScript_restartJob")

def executeScript_processMining(request):
    body_unicode = request.body.decode('utf-8')
    config = json.loads(body_unicode)
    format_config_parameters(config)

    filename = "config/config_%s.json" % config['JOB']['job_name']

    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()

    run([sys.executable,'BAW_to_IPM.py', filename], shell=False)
    # print(out)
    return HttpResponse("-- executeScript_processMining")

def stopExtraction(request) :
    body_unicode = request.body.decode('utf-8')
    body_json = json.loads(body_unicode)
    filename = "config/config_%s.json" % body_json['job_name']

    print("Stop execution with filename : %s" % filename)
    file = open(filename, 'r')
    config = json.load(file)
    config['JOB']['exit'] = 1
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()
    return HttpResponse("-- stopExtraction")

