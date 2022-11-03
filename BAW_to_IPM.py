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

PRINT_TRACE = 1
BACKUP_FILENAME = "BAW_IPM_backup.idp"
LOGGER_FILENAME = "BAW.log"
BAW_SERVER_TIME_ZONE = 0 # add or remove hours / greenwich timezone
CSV_PATH = "data/"


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


def main(argv):
    if (len(argv) == 1) :
        print("configuration file required")
        return

    logger = baw.setup_logger({"logfile" : LOGGER_FILENAME})

    # Open config/BAW_exclude_fields.json that contains the common fields that we don't need
    with open('config/BAW_default_fields.json', 'r') as file:
        baw_fields = json.load(file)
    # TODO: We need to take the default BAW_fields json file or the job specific one.

    
    while(1):
        with open(argv[1], 'r') as file:
            config = json.load(file) # keep the original
            file.close()
            print("--- Configuration file %s loaded" % argv[1])
        with open(argv[1], 'r') as file:
            run_config = json.load(file) # used to run the extraction with modified values
            file.close()
        #print(config)
        if (config['JOB']['exit'] == 1) :
            # Exit requested
            config['JOB']['exit'] = 0
            with open(argv[1], 'w') as file:
                json.dump(config, file, indent=4)
                file.close()
            print("Exit from extraction job %s" % config['JOB']['job_name'])
            exit() 


        # copy the config into a run_config
        ipm_config = config['IPM']
        ipm_config["backup_filename"] = BACKUP_FILENAME
        job_name = config['JOB']['job_name']

        # Adjust the time entered by the user to the BAW Server Time Zone
        now = datetime.fromtimestamp(time.time())
        time_adjust = timedelta(hours=BAW_SERVER_TIME_ZONE)
        now = now + time_adjust

        # run_config is what is being used at each execution
        # BAW auth
        run_config['BAW']['BAW_fields'] = baw_fields
        run_config['BAW']['auth_data'] = HTTPBasicAuth(run_config['BAW']['user'], run_config['BAW']['password'])

        print("Starting extraction for job name: %s" % run_config['JOB']['job_name'])
        # different situations depending on the config parameters
        if (config['JOB']['update_rate'] and config['BAW']['extraction_interval']):
            if (config['BAW']['modified_after'] == ""):
                print("Error: Modified After date is required for loops with an extraction interval")
                exit()
            else:
                config_with_extraction_interval(config, run_config)
              
        elif (config['JOB']['update_rate']):
            config_without_extraction_interval(config, run_config)


        event_data = []
        baw.extract_baw_data(event_data, run_config['BAW'], logger)

        # Update config for the next execution (as a loop or a restart)
        #if (update_rate and extraction_interval and (modified_after!= " ")) :
        if (config['JOB']['update_rate']):
            config['BAW']['last_after'] = run_config['BAW']['modified_after']
            # TODO: should we do this in all cases
            config['BAW']['last_before'] = run_config['BAW']['modified_before']

        if (event_data == []) :
            print("No data extracted")
        else:
            run_config['BAW']['csvfilename'] = "%s_%s_%d" % ("BAW", job_name, time.time_ns()/1000000)
            run_config['BAW']['csvpath'] = CSV_PATH
            baw.generate_csv_file(event_data, run_config['BAW'])
            print("Data Extraction Done")

            if (ipm_config['url']!=""):
                # automatic upload to IBM Process Mining
                print("Initialize event log upload")
                ipm_config['csv_filename'] = run_config['BAW']['csvpath']+run_config['BAW']['csvfilename']+".zip"
                if (ipm_config['project_key']):
                    # If 'project_key' is set, load to existing project
                    r = ipm.upload_csv_and_createlog(ipm_config)
                    if (r):
                        print("Event-log added to Process Mining project %s" % ipm_config['project_key'])
                    else : 
                        print("Event-log upload failed")
                else :
                    # create a new project and upload
                    r = ipm.create_and_load_new_project(ipm_config)
                    if (r.status_code == 200) : 
                        print("Process Mining: Process created %s" % ipm_config['project_name'])
                        print(r.json())
                        projectkey = r.json()['projectKey']
                        config['IPM']['project_key'] = projectkey
                    else :
                        print("Process Mining: Process creation failed")
        # Store the BAW config with the latest update, such that the user can restart from where he stopped

        with open(argv[1], 'w') as file:
            json.dump(config, file, indent=4)
            file.close()

        if (config['JOB']['update_rate'] == 0):
            print("update_rate = 0, process terminated")
            exit()
        print("Next update in %s seconds" % config['JOB']['update_rate'])
        time.sleep(config['JOB']['update_rate'])

if __name__ == "__main__":
    main(sys.argv)
