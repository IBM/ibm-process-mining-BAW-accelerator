from multiprocessing.dummy import JoinableQueue
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.shortcuts import render
import json
import sys
from subprocess import run
import re

import bawjobs
from .models import Bawjobs

def getDefaultConfig():
    return {
        "JOB": {
            "job_name": "",
            "update_rate": 0,
            "exit": 0
        },
        "BAW": {
            "root_url": "",
            "user": "",
            "password": "",
            "password_env_var": "",
            "project": "",
            "process_name": "",
            "modified_after": "",
            "modified_before": "",
            "extraction_interval": 0,
            "thread_count": 1,
            "instance_limit": -1,
            "task_data_variables": [],
            "export_exposed_variables": False,
            "csv_at_each_loop": False,
            "last_after": "",
            "last_before": ""
        },
        "IPM": {
            "url": "",
            "user_id": "",
            "api_key": "",
            "org_key": "",
            "project_key": "",
            "version": "1.13.1+"
        }
    }

def convert_date(request, config, key, fieldname):
    if key in request.POST:
        if request.POST[key] == "": 
            config['BAW'][fieldname] = ""
        else:
            # yyyy-mm-dd hh:mm:ss if time=00:00:00 we get only 00:00, so add the seconds
            if (request.POST[key][11:] == "00:00" ): 
                config['BAW'][fieldname] = request.POST[key]+":00Z"
            else:
                config['BAW'][fieldname] = request.POST[key]+"Z"

def get_values_from_webUI(request, config):

    # correct the BAW URL (expect / at the end)
    if "baw_root_url" in request.POST:
        root_url = request.POST['baw_root_url']
        if (root_url[-1] != '/'): 
            root_url = root_url+"/"
        config['BAW']['root_url'] = root_url

    # correct the IPM URL (does not expect / at the end)
    if 'ipm_url' in request.POST:
        ipm_url = request.POST['ipm_url']
        if (ipm_url != ""):
            if (ipm_url[-1] == '/'):
                ipm_url = ipm_url[:-1]
        config['IPM']['url'] = ipm_url

    # get the dates/time from widgets and transform into a date string (add Z at the end)
    # the function does nothing if the key is not in request.POST
    convert_date(request, config, 'baw_modified_before', 'modified_before')
    convert_date(request, config, 'baw_modified_after', 'modified_after')
    convert_date(request, config, 'baw_last_after', 'last_after')
    convert_date(request, config, 'baw_last_before', 'last_before')

    # baw_update_rate is a string returned by a input of type time. Convert into seconds
    if('baw_update_rate' in request.POST):
        if request.POST['baw_update_rate'] == "":
            config['JOB']['update_rate'] = 0
        else:
            x = request.POST['baw_update_rate'].split(':') # value could be "00:00:00"
            if len(x)==2: config['JOB']['update_rate'] = 0
            else: config['JOB']['update_rate'] = 3600 * int(x[0]) + 60 * int(x[1]) + int(x[2])

    if ('baw_extraction_interval' in request.POST):
        config['BAW']['extraction_interval'] = int(request.POST['baw_extraction_interval'])

    if ('baw_thread_count' in request.POST):
        config['BAW']['thread_count'] = int(request.POST['baw_thread_count'])

    if ('baw_instance_limit' in request.POST):
        config['BAW']['instance_limit'] = int(request.POST['baw_instance_limit'])

    if ('baw_task_data_variables' in request.POST):
        if (request.POST['baw_task_data_variables'] == ""):
            config['BAW']['task_data_variables'] = []
        else:
            s=request.POST['baw_task_data_variables']
            s=re.sub(';',',', s)
            # to be sure, if the latest char is "," remove it
            if s[-1] == "," : s= s[:-1]
            s=re.sub('(\s)','',s )
            s=re.sub('(\n)','',s )
            config['BAW']['task_data_variables'] = s.split(',')
    
    # check box
    if 'baw_export_exposed_variables' in request.POST:
        # means that the check box is on
        if (request.POST['baw_export_exposed_variables'] == 'on'):
            config['BAW']['export_exposed_variables'] = True
        else:
            config['BAW']['export_exposed_variables'] = False

    if 'baw_csv_at_each_loop' in request.POST:
        # means that the check box is on
        if (request.POST['baw_csv_at_each_loop'] == 'on'):
            config['BAW']['csv_at_each_loop'] = True
        else:
            config['BAW']['csv_at_each_loop'] = False

    if 'job_name' in request.POST:
        config['JOB']['job_name'] = request.POST['job_name']
    if 'baw_user' in request.POST:
        config['BAW']['user'] = request.POST['baw_user']
    if 'baw_password' in request.POST:
        config['BAW']['password'] = request.POST['baw_password']
    if 'baw_password_env_var' in request.POST:
        config['BAW']['password_env_var'] = request.POST['baw_password_env_var']
    if 'baw_project' in request.POST:
        config['BAW']['project'] = request.POST['baw_project']
    if 'baw_process_name' in request.POST:
        config['BAW']['process_name'] = request.POST['baw_process_name']
    if 'ipm_user_id' in request.POST: 
        config['IPM']['user_id'] = request.POST['ipm_user_id']
    if 'ipm_api_key' in request.POST:
        config['IPM']['api_key'] = request.POST['ipm_api_key']    
    if 'ipm_org_key' in request.POST:
        config['IPM']['org_key'] = request.POST['ipm_org_key']

    if 'ipm_project_key' in request.POST:
        config['IPM']['project_key'] = re.sub(' ', '-', request.POST['ipm_project_key'])


def set_context_from_config(config):
    # Get the data from the config file and transform them to fit with the values expected in the form
    if (config['BAW']['modified_after'] != ""):
        # remove the last Z
        baw_modified_after = config['BAW']['modified_after'][:-1]
    else:
        baw_modified_after = ""

    if (config['BAW']['modified_before'] != ""):
        baw_modified_before = config['BAW']['modified_before'][:-1]
    else:
        baw_modified_before = ""

        # data from previous run
    if (config['BAW']['last_after'] != ""):
        baw_last_after = config['BAW']['last_after'][:-1]
    else:
        baw_last_after = ""

    if (config['BAW']['last_before'] != ""):
        baw_last_before = config['BAW']['last_before'][:-1]
    else:
        baw_last_before = ""

    # this is an array with variable names
    # concatenate the variable names, separated with a comma
    task_data_variables = ",".join(config['BAW']['task_data_variables'])
    # to be sure, if the last char is a ',' remove it
    if len(task_data_variables)>0 and task_data_variables[-1] =="," : task_data_variables = task_data_variables[:-1]

    # set the version
    if (config['IPM']['version']=="1.13.1+"):
        version1131 = "selected"
        version1130 = ""
    else: 
        version1131 = ""
        version1130 = "selected"
    
    # update rate is now set with a time widget. Transform seconds in json file into HH:MM:SS
    update_rate = config['JOB']['update_rate']
    m, s = divmod(update_rate, 60)
    h, m = divmod(m, 60)
    baw_update_rate = f'{h:02d}:{m:02d}:{s:02d}'

    # export_exposed_variables is true set the checkbox to on
    if (config['BAW']['export_exposed_variables'] == True):
        baw_exposed_variables = 'checked'
    else: baw_exposed_variables = ''

    # csv at each loop
    if (config['BAW']['csv_at_each_loop'] == True):
        baw_csv_at_each_loop = 'checked'
    else: baw_csv_at_each_loop = ''

    context = {
        'config': config,
        'baw_modified_after' : baw_modified_after,
        'baw_modified_before': baw_modified_before,
        'baw_last_after' : baw_last_after,
        'baw_last_before' : baw_last_before,
        'baw_task_data_variables' : task_data_variables,
        'imp_selected_version1131' : version1131,
        'ipm_selected_version1130': version1130,
        'baw_update_rate': baw_update_rate,
        'baw_exposed_variables': baw_exposed_variables,
        'baw_csv_at_each_loop': baw_csv_at_each_loop
    }
    return context

# FUNCTIONS ASSIGNED TO VIEWS and URLS
def index(request):
    mybawjobs = Bawjobs.objects.all().values()
    template = loader.get_template('index.html')
    context = {
        'mybawjobs': mybawjobs,
        }
    return HttpResponse(template.render(context, request))

# JOB CREATION FUNCTIONS
# createjob initiates the creation page with an empty config
#  
def createjob(request):
    template = loader.get_template('createjob.html')
    # init the web UI with a default configuration such that each field has a correct value
    config = getDefaultConfig()

    context = set_context_from_config(config)
    return HttpResponse(template.render(context, request))

# addjob get the data back from the form and create the final config to be saved
def addjob(request):
    
    # Init the JSON configuration. Fields that require transformation from the UI are processed after
    config = getDefaultConfig()

  # Fields that require processing from the POST values are processed 
    get_values_from_webUI(request, config)

    filename = "config/config_%s.json" % request.POST['job_name']
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()

    # When everything is done, save the job in the Django DB
    newjob = Bawjobs(
        job_name = config['JOB']['job_name'],
        root_url = config['BAW']['root_url'],
        project = config['BAW']['project'],
        process_name = config['BAW']['process_name'],
        ipm_url = config['IPM']['url'],
        ipm_project_key = config['IPM']['project_key']
    )
    newjob.save()
    
    return HttpResponseRedirect(reverse('index'))

# JOB DELETE 
# createjob initiates the creation page with an empty config
#  
def delete(request, id):
    bawjob = Bawjobs.objects.get(id=id)
    bawjob.delete()
    return HttpResponseRedirect(reverse('index'))

# EXISTING JOB EDITING 
# createjob initiates the creation page with an empty config
#  
def edit(request, id):
    bawjob = Bawjobs.objects.get(id=id)
    template = loader.get_template('updateJob.html')
    filename = "config/config_%s.json" % bawjob.job_name
    print("Load filename : %s" % filename)
    file = open(filename, 'r')
    config = json.load(file)
    file.close()

    context = set_context_from_config(config)
    context['bawjob'] = bawjob
    return HttpResponse(template.render(context, request))
    
def savejob(request, id):
    bawjob = Bawjobs.objects.get(id=id)
    print("job saved :"+bawjob.job_name)

    # Retrieve the data from the web UI 
    config = getDefaultConfig()
    # job_name is not editable in the 'edit' web UI. We pick it from the object
    config['JOB']['job_name'] = bawjob.job_name

    # Fields that require processing from the POST values are processed 
    get_values_from_webUI(request, config)
    # Save the configuration
    filename = "config/config_%s.json" % bawjob.job_name
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()

    # Update the bawjob
    bawjob.root_url = config['BAW']['root_url']
    bawjob.project = config['BAW']['project']
    bawjob.process_name = config['BAW']['process_name']
    bawjob.ipm_url = config['IPM']['url']
    bawjob.ipm_project_name = config['IPM']['project_name']
    bawjob.ipm_project_key = config['IPM']['project_key']

    print(bawjob.process_name)
    # save
    bawjob.save()

    return HttpResponseRedirect(reverse('index'))

# Copy an existing job configuration and save it under another name
def copy(request, id):
    bawjob = Bawjobs.objects.get(id=id)
    template = loader.get_template('createjob.html')
    filename = "config/config_%s.json" % bawjob.job_name
    print("Load filename : %s" % filename)
    file = open(filename, 'r')
    config = json.load(file)
    file.close()

    config['JOB']['job_name']=""
    context = set_context_from_config(config)
    
    return HttpResponse(template.render(context, request))

# RUNNING EXTRACTION 
#
#   

def initextraction(request, id):
    bawjob = Bawjobs.objects.get(id=id)
    template = loader.get_template('startJob.html')
    filename = "config/config_%s.json" % bawjob.job_name
    print("Load filename : %s" % filename)
    file = open(filename, 'r')
    config = json.load(file)
    file.close()

    context = set_context_from_config(config)
    context['mybawjob']= bawjob

    return HttpResponse(template.render(context, request))

def startextraction(request, id):
    print("start extraction")
    Bawjob = Bawjobs.objects.get(id=id)
    job_name = Bawjob.job_name

    # Load config file
    filename = "config/config_%s.json" % job_name
    file = open(filename, 'r')
    config = json.load(file)
    file.close()

    get_values_from_webUI(request, config)

    # save the config file
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()

    # Start the extraction python code in a subprocess
    completedStatus = run([sys.executable,'BAW_to_IPM.py', filename], shell=False) 
    context = {
        'config': config,
        'return_code': completedStatus.returncode
        }
    template = loader.get_template('extractioncomplete.html')
    return HttpResponse(template.render(context, request))

def stopextraction(request, id):
    print('stop extraction')
    Bawjob = Bawjobs.objects.get(id=id)
    job_name = Bawjob.job_name
    # Load config file
    filename = "config/config_%s.json" % job_name
    file = open(filename, 'r')
    config = json.load(file)
    file.close()

    config['JOB']['exit'] = 1
    # save the config file
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4)
        file.close()

    context = {
        'job_name': job_name,
        'return_code': 0
        }
    template = loader.get_template('extractioncomplete.html')
    return HttpResponse(template.render(context, request))
    #return HttpResponseRedirect(render('extractioncomplete/'+str(id)))

def extractioncomplete(request,id):
    return render(request, "extractioncomplete.html")

