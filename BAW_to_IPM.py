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

PRINT_TRACE = 1
BACKUP_FILENAME = "BAW_IPM_backup.idp"
BAW_SERVER_TIME_ZONE = 0 # add or remove hours / greenwich timezone
CSV_PATH = "data/"
EVENT_NUMBER_THRESHOLD = 500000 # used when historical extraction with time period. When we pass this number, we create a CSV file


def config_with_extraction_interval(config, run_config):
    if (config['BAW']['last_after'] == ""):
        # for the first run we just keep modified_after as specified in the configuration file
        # the instruction below is not needed since this is already the case. We keep it for clarity
        run_config['BAW']['modified_after']=config['BAW']['modified_after']
    else:
        # next run of a loop with a period
        run_config['BAW']['modified_after']=config['BAW']['last_before']

    # compute the extraction interval
    extraction_interval = timedelta(days=config['BAW']['extraction_interval'])

    # compute the run_before as the minimum between after+period and modified_before if any
    run_before = datetime.strptime(run_config['BAW']['modified_after'], "%Y-%m-%dT%H:%M:%SZ") + extraction_interval

    # if there is a modified_before date in the config file, we need to stop when we reach this date
    if (config['BAW']['modified_before'] != ""):
        # There is a modified_before limit set by the user
        run_before_max = datetime.strptime(config['BAW']['modified_before'], "%Y-%m-%dT%H:%M:%SZ")
        if (run_before > run_before_max):
            config['JOB']['exit'] = 1
            run_config['BAW']['modified_before'] = config['BAW']['modified_before']
        else:
            run_config['BAW']['modified_before'] = run_before.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # No modified before limit set by the user, current date is the limit for the run
        # If run_before > run_before_now, we take run_before_now
        # WARNING: the BAW server might use another time, it might be needed to adjust the time
        run_before_now = datetime.fromtimestamp(time.time())
        if (run_before > run_before_now):
            run_config['BAW']['modified_before'] = run_before_now.strftime("%Y-%m-%dT%H:%M:%SZ")
            # we start runtime updates. Should we exit? and then we have runtime update jobs for updates
            # the difference between runtime updates and extraction interval is that we would keep the same CSV for extraction interval instead
            # of sending a new one for each period. And for the update we would need a different update loop rate
            # exit at next loop

            config['JOB']['exit'] = 1
        else:
            run_config['BAW']['modified_before'] = run_before.strftime("%Y-%m-%dT%H:%M:%SZ")

def config_without_extraction_interval(config, run_config):
    # no extraction_interval, first run get everything until now, next get new data
    if (config['BAW']['last_before'] == ""):
        # first run get everything until now, next get new data
        # instruction below not needed, but kept for clarity
        run_config['BAW']['modified_after'] = config['BAW']['modified_after']
    else:
        # next runs start at last_before (was now during the last execution)
        run_config['BAW']['modified_after'] = config['BAW']['last_before']
    now = datetime.fromtimestamp(time.time())
    run_config['BAW']['modified_before'] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

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

def run_extraction(event_data, config, run_config, logger):
    # run_config is what is being used at each execution
    # BAW auth
    #run_config['BAW']['auth_data'] = HTTPBasicAuth(run_config['BAW']['user'], run_config['BAW']['password'])
    run_config['BAW']['auth_data'] = get_BAW_auth(config['BAW'], logger)

    # different situations depending on the config parameters: is there an update rate? is there an extraction interval?
    if (config['JOB']['update_rate'] and config['BAW']['extraction_interval']):
        if (config['BAW']['modified_after'] == ""):
            print("Error: Modified After date is required for loops with an extraction interval")
            exit()
        else:
            config_with_extraction_interval(config, run_config)    
              
    elif (config['JOB']['update_rate']):
        config_without_extraction_interval(config, run_config)
        
    # reset the event_data array where we add all the events
    baw.extract_baw_data(event_data, run_config['BAW'], logger)

    # Update original config for the next execution (as a loop or a restart)
    # if (update_rate and extraction_interval and (modified_after!= " ")) :
    if (config['JOB']['update_rate']):
        config['BAW']['last_after'] = run_config['BAW']['modified_after']
        config['BAW']['last_before'] = run_config['BAW']['modified_before']
    
    return event_data

def generate_csv(event_data, run_config):
    run_config['BAW']['csvfilename'] = "%s_%s_%d" % ("BAW", run_config['JOB']['job_name'], time.time_ns()/1000000)
    run_config['BAW']['csvpath'] = CSV_PATH
    return baw.generate_csv_file(event_data, run_config['BAW'])

def upload_csv(run_config, config, logger):
    print("uploading")
    r = ipm.ws_post_sign(run_config['IPM'])
    if (r==0):
        print("Error getting the signature for Process Mining")
        logger.error("Error getting the signature for Process Mining")
        exit
    else:
        run_config['IPM']['sign'] = r

    #print("Initialize event log upload")

    if (run_config['IPM']['project_key']):
        # If 'project_key' is mandatory, it exists or not (then create the project)
        # Replace ' ' with '-'
        run_config['IPM']['project_key']=re.sub(' ','-', run_config['IPM']['project_key'])
        # test if the project_key exists
        r = ipm.ws_get_project_info(run_config['IPM'])
        if (r.status_code == 200):
            r = ipm.upload_csv_and_createlog(run_config['IPM'])
            if (r):
                print("Event-log added to Process Mining project %s" % run_config['IPM']['project_key'])
                logger.info("Event-log added to Process Mining project %s" % run_config['IPM']['project_key'])
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
                run_config['IPM']['project_name'] = run_config['IPM']['project_key']
                r = ipm.create_and_load_new_project(run_config['IPM'])
                if (r.status_code == 200) : 
                    print("Process Mining: Process created %s" % run_config['IPM']['project_name'])
                    logger.info("Process Mining: Process created %s" % run_config['IPM']['project_name'])
                    projectkey = r.json()['projectKey']
                    config['IPM']['project_key'] = projectkey
                else :
                    print("Process Mining: Process creation failed")
                    logger.info("Process Mining: Process creation failed")
            elif (r.status_code == 401):
                print("unauthorized access to processmining")
                logger.error("unauthorized access to processmining")



def main(argv):
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
        with open(argv[1], 'r') as file:
            run_config = json.load(file) # used to run the extraction with modified values
            file.close()



        # if update_rate == 0, exit at the next loop -- to be set on run_config (executed)
        if (config['JOB']['update_rate'] == 0):
            run_config['JOB']['exit'] = 1
        run_config['BAW']['BAW_fields'] = baw_fields
        run_config['IPM']["backup_filename"] = BACKUP_FILENAME
        run_config['BAW']['event_number_threshold'] = EVENT_NUMBER_THRESHOLD


        # Adjust the time entered by the user to the BAW Server Time Zone
        now = datetime.fromtimestamp(time.time())
        time_adjust = timedelta(hours=BAW_SERVER_TIME_ZONE)
        now = now + time_adjust

        print("Starting extraction for job name: %s" % run_config['JOB']['job_name'])
        run_extraction(event_data, config, run_config, logger)

        if (event_data != []) :
            if ((run_config['JOB']['exit'] == 1) or 
            (len(event_data) >= run_config['BAW']['event_number_threshold']) or
            run_config['BAW']['csv_at_each_loop'] == True):
                # exit == 1 if job stopped, or modified_before date is reached, or update_loop==0
                # event_number_threshold only for historical with interval period. To be set before
                csvzipfilepath = generate_csv(event_data, run_config)
                # re-initialize event_data
                event_data = []
                if (run_config['IPM']['url']!=""):
                    # automatic upload to IBM Process Mining
                    run_config['IPM']['csv_filename'] = csvzipfilepath
                    upload_csv(run_config, config, logger)

        # Store the BAW config with the latest update, such that the user can restart from where he stopped
        with open(argv[1], 'w') as file:
            json.dump(config, file, indent=4)
            file.close()

        if ((config['JOB']['exit'] == 1) or (run_config['JOB']['exit'] == 1)) :
            # Exit requested or required when before_date is reached, or when loop_rate == 0 (no loop)
            config['JOB']['exit'] = 0
            with open(argv[1], 'w') as file:
                json.dump(config, file, indent=4)
                file.close()
            print("Exit from extraction job %s" % config['JOB']['job_name'])
            exit() 

        # Sleep until the next loop
        time.sleep(config['JOB']['update_rate'])

if __name__ == "__main__":
    main(sys.argv)
