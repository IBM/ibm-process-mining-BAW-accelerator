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
            "exit": 0
        },
        "BAW": {
            "root_url": "",
            "user": "",
            "password": "",
            "password_env_var": "",
            "project": "",
            "process_name": "",
            "from_date": "",
            "from_date_criteria": "modified",
            "to_date": "",
            "to_date_criteria": "modified",
            "paging_size": 0,
            "status_filter": "Active,Completed,Failed,Terminated,Suspended,Late,At_Risk",
            "loop_rate": 0,
            "thread_count": 1,
            "instance_limit": 0,
            "offset": 0,
            "task_data_variables": [],
            "export_exposed_variables": False,
            "csv_at_each_loop": False,
            "trigger_csv_beyond": 500000
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
    convert_date(request, config, 'baw_from_date', 'from_date')
    convert_date(request, config, 'baw_to_date', 'to_date')

    if('baw_loop_rate' in request.POST):
        config['BAW']['loop_rate'] = int(request.POST['baw_loop_rate'])

    if ('baw_thread_count' in request.POST):
        config['BAW']['thread_count'] = int(request.POST['baw_thread_count'])

    if ('baw_instance_limit' in request.POST):
        config['BAW']['instance_limit'] = int(request.POST['baw_instance_limit'])

    if ('baw_offset' in request.POST):
        config['BAW']['offset'] = int(request.POST['baw_offset'])

    if ('baw_paging_size' in request.POST):
        config['BAW']['paging_size'] = int(request.POST['baw_paging_size'])

    if ('baw_trigger_csv_beyond' in request.POST):
        config['BAW']['trigger_csv_beyond'] = int(request.POST['baw_trigger_csv_beyond'])

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
        config['BAW']['export_exposed_variables'] = True
    else:
        config['BAW']['export_exposed_variables'] = False
    
    if 'baw_from_date_criteria' in request.POST:
        config['BAW']['from_date_criteria'] = request.POST['baw_from_date_criteria']

    if 'baw_to_date_criteria' in request.POST:
        config['BAW']['to_date_criteria'] = request.POST['baw_to_date_criteria']

    if 'baw_statusFilter' in request.POST:
        # means that the check box is on
        config['BAW']['statusFilter'] = request.POST['baw_statusFilter']
  
    if 'baw_csv_at_each_loop' in request.POST:
        # means that the check box is checked
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
    if 'ipm_version' in request.POST:
        config['IPM']['version'] = request.POST['ipm_version']

    if 'ipm_project_key' in request.POST:
        config['IPM']['project_key'] = re.sub(' ', '-', request.POST['ipm_project_key'])


def set_context_from_config(config):
    # Get the data from the config file and transform them to fit with the values expected in the form
    if (config['BAW']['from_date'] != ""):
        # remove the last Z
        baw_from_date = config['BAW']['from_date'][:-1]
    else:
        baw_from_date = ""

    # set the from date criteria
    if (config['BAW']['from_date_criteria']=="modifiedAfter"):
        selected_modified_after = "selected"
        selected_created_after = ""
        selected_closed_after = ""
    elif (config['BAW']['from_date_criteria']=="createdAfter"):
        selected_modified_after = ""
        selected_created_after = "selected"
        selected_closed_after = ""
    else:
        selected_modified_after = ""
        selected_created_after = ""
        selected_closed_after = "selected"

    if (config['BAW']['to_date'] != ""):
        baw_to_date = config['BAW']['to_date'][:-1]
    else:
        baw_to_date = ""

   # set the to date criteria
    if (config['BAW']['to_date_criteria']=="modifiedBefore"):
        selected_modified_before = "selected"
        selected_created_before = ""
        selected_closed_before = ""
    elif (config['BAW']['to_date_criteria']=="createdBefore"):
        selected_modified_before = ""
        selected_created_before = "selected"
        selected_closed_before = ""
    else:
        selected_modified_before = ""
        selected_created_before = ""
        selected_closed_before = "selected"

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
    #loop_rate = config['BAW']['loop_rate']
    #m, s = divmod(loop_rate, 60)
    #h, m = divmod(m, 60)
    #baw_loop_rate = f'{h:02d}:{m:02d}:{s:02d}'


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
        'baw_from_date' : baw_from_date,
        'baw_to_date': baw_to_date,
        'baw_task_data_variables' : task_data_variables,
        'imp_selected_version1131' : version1131,
        'ipm_selected_version1130': version1130,
        'baw_exposed_variables': baw_exposed_variables,
        'baw_csv_at_each_loop': baw_csv_at_each_loop,
        'selected_modified_after': selected_modified_after,
        'selected_created_after': selected_created_after,
        'selected_closed_after': selected_closed_after,
        'selected_modified_before': selected_modified_before,
        'selected_created_before': selected_created_before,
        'selected_closed_before': selected_closed_before
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
    bawjob.ipm_project_key = config['IPM']['project_key']

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

def loadjsonfile(request):
    template = loader.get_template('loadjsonfile.html')
    # init the web UI with a default configuration such that each field has a correct value
    config = getDefaultConfig()

    context = set_context_from_config(config)
    return HttpResponse(template.render(context, request))

def recordjsonfile(request):

    filename = "config/"+request.POST['jsonfile']
    print("Load filename : %s" % filename)
    file = open(filename, 'r')
    config = json.load(file)
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