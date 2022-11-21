from curses.panel import update_panels
from warnings import catch_warnings
import BAWExtraction_utils as baw
import ProcessMining_utils as ipm
import json
import time
from time import gmtime, strftime
from datetime import datetime, date, timedelta
import sys
from requests.auth import HTTPBasicAuth
import os
import logging
import re
import asyncio


PRINT_TRACE = 1
BACKUP_FILENAME = "BAW_IPM_backup.idp"
BAW_SERVER_TIME_ZONE = 0 # add or remove hours / greenwich timezone
CSV_PATH = "data/"

def  config_with_loop_and_interval_shift(now, config):
    if (config['BAW']['last_before'] != ""):
        # next loop (for the first one, we just extract with the dates)
        # compute the next interval from the duration between after and before
        after = datetime.strptime(config['BAW']['modified_after'], "%Y-%m-%dT%H:%M:%SZ")
        before = datetime.strptime(config['BAW']['modified_before'], "%Y-%m-%dT%H:%M:%SZ")
        duration = before - after
        last_before = datetime.strptime(config['BAW']['last_before'], "%Y-%m-%dT%H:%M:%SZ")
        config['BAW']['modified_after'] = config['BAW']['last_before']
        before = last_before + duration
        config['BAW']['modified_before'] = before.strftime("%Y-%m-%dT%H:%M:%SZ")
        # stop when modified_before >= now
        if (before >= now):
            config['BAW']['modified_before'] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            config['JOB']['exit'] = 1

def config_for_near_real_time_update(now, config):
    # loop to get new data. 'modified_after' can be set, 'modified_before' must be """, executed with now
    config['BAW']['modified_before'] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    # first loop get everything until now, next get new data
    if (config['BAW']['last_before'] != ""):
        # next loop start at last_before
        config['BAW']['modified_after'] = config['BAW']['last_before']

def config_for_instance_limit(now, instance_list, config):
    if (instance_list == []):
        # get instances, modified_after and modified_before are optional
        if (config['BAW']['modified_before'] == ""):
            config['BAW']['modified_before'] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            if (config['BAW']['last_before'] != ""):
                # Another loop where we need to extract new instances for near real time updates
                config['BAW']['modified_after'] = config['BAW']['last_before']
    else:
        # next loops where we continue processing the instance_list, without fetching instances from BAW: keep same dates as before. 
        config['BAW']['modified_before'] = config['BAW']['last_before']
        if (instance_list is not None and len(instance_list) <= config['BAW']['instance_limit']):
            #if instance_list size < instance_limit, that's the last loop, exit if modified_before is set
            if (config['BAW']['modified_before'] != "") and config['BAW']['interval_shift'] != True:
                # We stop when we are done, except is interval_shift is true, in which case we should continue until now
                print("config_with_loop_and_instance_limit: last extraction before exit %s" % len(instance_list))
                config['JOB']['exit'] = 1

def run_extraction(now, instance_list, event_data, config, logger):
    # run_config is what is being used at each execution
    # BAW auth
    # run_config['BAW']['auth_data'] = get_BAW_auth(config['BAW'], logger)
    config['BAW']['auth_data'] = get_BAW_auth(config['BAW'], logger)
    modified_after_orig = config['BAW']['modified_after']
    modified_before_orig = config['BAW']['modified_before']

    # loop_rate : different scenarios depending on the config parameters
    if config['BAW']['loop_rate'] != 0 :
        if config['BAW']['interval_shift'] == True:
            # there must be an interval, and we shift it at each loop
            if config['BAW']['modified_after'] == "" or config['BAW']['modified_before'] == "":
                print("Error: Modified After date is required for loops with an extraction interval")
                config['JOB']['exit'] = 1
                return [], []
            else:
                config_with_loop_and_interval_shift(now, config)        
        elif config['BAW']['instance_limit'] == 0 and config['BAW']['modified_before'] == "":
            config_for_near_real_time_update(now, config)
        if config['BAW']['instance_limit'] > 0:
            config_for_instance_limit(now, instance_list, config)
    
    instance_list = baw.extract_baw_data(instance_list, event_data, config['BAW'], logger)

    # Remember what was the last extraction, such that we don't get the same data again during the next loop
    config['BAW']['last_before'] = config['BAW']['modified_before']
    # Bring back original data in config such that it can be saved at the end of the loop without loosing the original intent
    config['BAW'].pop('auth_data')
    config['BAW']['modified_after'] = modified_after_orig
    config['BAW']['modified_before'] = modified_before_orig

    return event_data, instance_list

def get_BAW_auth(config, logger):

    if (config['password_env_var'] != ""):
        #print("environment vars: %s" % os.environ)
        pwd = os.getenv(config['password_env_var'])
    
        if pwd is None: # no env variable set
            print(f"Error environment variable: {config['password_env_var']} for BAW password not found")
            if (config['password']!= ""):
                # try with the password
                pwd = config['password']
            else :# no pwd set in the config file
                print("BAW extraction error: missing password")
                logger.info("BAW extraction error: missing password")
                return 0    
    else : # use the password
        pwd = config['password']
    return(HTTPBasicAuth(config['user'], pwd))

def generate_csv(event_data, run_config):
    run_config['BAW']['csvfilename'] = "%s_%s_%d" % ("BAW", run_config['JOB']['job_name'], time.time_ns()/1000000)
    run_config['BAW']['csvpath'] = CSV_PATH
    return baw.generate_csv_file(event_data, run_config['BAW'])

def upload_csv(config, logger):
    print("uploading")
    r = ipm.ws_post_sign(config['IPM'])
    if (r==0):
        print("Error getting the signature for Process Mining")
        logger.error("Error getting the signature for Process Mining")
        exit
    else:
        config['IPM']['sign'] = r

    #print("Initialize event log upload")

    if (config['IPM']['project_key']):
        # If 'project_key' is mandatory, it exists or not (then create the project)
        # Replace ' ' with '-'
        config['IPM']['project_key']=re.sub(' ','-', config['IPM']['project_key'])
        # test if the project_key exists
        r = ipm.ws_get_project_info(config['IPM'])
        if (r.status_code == 200):
            r = ipm.upload_csv_and_createlog(config['IPM'])
            if (r):
                print("Event-log added to Process Mining project %s" % config['IPM']['project_key'])
                logger.info("Event-log added to Process Mining project %s" % config['IPM']['project_key'])
            else : 
                print("Event-log upload failed")
                logger.info("Event-log upload failed")

        elif (r.status_code == 400):
            if (r.json()['error'] == 1001):
                # error with organization
                print(r.json()['data']['data'])
                logger.error(r.json()['data']['data'])
            elif (r.json()['error'] == 1002):
                # project does not exist, create it and upload
                config['IPM']['project_name'] = config['IPM']['project_key']
                r = ipm.create_and_load_new_project(config['IPM'])
                if (r.status_code == 200) : 
                    print("Process Mining: Process created %s" % config['IPM']['project_name'])
                    logger.info("Process Mining: Process created %s" % config['IPM']['project_name'])
                    projectkey = r.json()['projectKey']
                    config['IPM']['project_key'] = projectkey
                else :
                    print("Process Mining: Process creation failed")
                    logger.info("Process Mining: Process creation failed")
            elif (r.status_code == 401):
                print("unauthorized access to processmining")
                logger.error("unauthorized access to processmining")


def main(argv):
    #debug
    if (argv == []) : argv=["","config/config_newBAWextract.json"]
    if (len(argv) == 1) :
        print("configuration file required")
        return

    # Open config/BAW_default_fields.json that contains the mappings, the included and excluded fields
    with open('config/BAW_default_fields.json', 'r') as file:
        baw_fields = json.load(file)
    # TODO: We need to take the default BAW_fields json file or the job specific one.

    # array for the event log. Initiated before the loop.
    # the event_data will be copied in a CSV file at each loop (runtime scenario) or when a size is reached (historical scenario)
    # for historical scenario with extraction interval, we keep generate the csv only when the size limit is reached
    event_data = []
    run_config = {}
    instance_list = []

    # We need one logger per JOB. Save logs into logs/job_name.log
    with open(argv[1], 'r') as file:
        config = json.load(file) # keep the original
        file.close()
    logger = baw.setup_logger({"logfile" : "logs/"+config['JOB']['job_name']+".log"}, logging.INFO)

    while(1):
        # read again the config file to catch changes (like exit=1)
        with open(argv[1], 'r') as file:
            config = json.load(file) # keep the original
            file.close()

       # Adjust the time entered by the user to the BAW Server Time Zone
        now = datetime.fromtimestamp(time.time())
        #print("Current local time = %s" % now.strftime("%Y-%m-%dT%H:%M:%SZ"))

        time_adjust = timedelta(hours=BAW_SERVER_TIME_ZONE)
        now = now + time_adjust
        #print("Current server time = %s" % now.strftime("%Y-%m-%dT%H:%M:%SZ"))

        # if loop_rate == 0, exit at the end of the run
        if (config['BAW']['loop_rate'] == 0):
            config['JOB']['exit'] = 1

        config['BAW']['BAW_fields'] = baw_fields
        config['IPM']["backup_filename"] = BACKUP_FILENAME


        print("Starting extraction for job name: %s" % config['JOB']['job_name'])
        result = run_extraction(now, instance_list, event_data, config, logger)
        event_data = result[0]
        instance_list = result[1]

        if (event_data != []) :
            if ((config['JOB']['exit'] == 1) or 
            (len(event_data) >= config['BAW']['event_number_csv_trigger']) or
            config['BAW']['csv_at_each_loop'] == True):
                # exit == 1 if job stopped, or modified_before date is reached, or update_loop==0
                # event_number_csv_trigger only for historical with interval period. To be set before
                csvzipfilepath = generate_csv(event_data, config)
                # re-initialize event_data
                event_data = []
                if (config['IPM']['url']!=""):
                    # automatic upload to IBM Process Mining
                    config['IPM']['csv_filename'] = csvzipfilepath
                    upload_csv(config, logger)

        # Store the BAW config with the latest update, such that the user can restart from where he stopped
        # Remove fields that we don't want to save
        baw_keys = config['BAW']
        if 'csvfilename' in baw_keys:
            config['BAW'].pop('csvfilename')
        if 'backup_filename' in baw_keys:
            config['BAW'].pop('backup_filename')
        if 'csvpath' in baw_keys:
            config['BAW'].pop('csvpath')       
        config['BAW'].pop('BAW_fields')

        ipm_keys = config['IPM'].keys() 
        if 'ts' in ipm_keys:
            config['IPM'].pop('ts')
        if 'sign' in ipm_keys:
            config['IPM'].pop('sign')
        if 'job_key' in ipm_keys:
            config['IPM'].pop('job_key')
        if 'backup_filename' in ipm_keys:
            config['IPM'].pop('backup_filename')
        if 'csv_filename' in ipm_keys:
            config['IPM'].pop('csv_filename')           

        # Save the configuration (last_before needs to be stored)
        with open(argv[1], 'w') as file:
            json.dump(config, file, indent=4)
            file.close()

        if config['JOB']['exit'] == 1:
            # Exit requested or required when before_date is reached, or when loop_rate == 0 (no loop)
            config['JOB']['exit'] = 0
            with open(argv[1], 'w') as file:
                json.dump(config, file, indent=4)
                file.close()
            print("Exit from extraction job %s" % config['JOB']['job_name'])
            exit() 

        # Sleep until the next loop
        time.sleep(config['BAW']['loop_rate'])

if __name__ == "__main__":
    main(sys.argv)
