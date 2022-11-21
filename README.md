# Accelerator for IBM Business Automation Workflow and IBM Process Mining
## NOTE
To obtain the librairies required to execute the accelerator, please contact Patrick Megard (patrick.megard@fr.ibm.com).
https://github.com/Patrick-Megard/ibm-process-mining-connectors-utils


## Introduction
This repository is a free contribution provided as-is to easily connect IBM Business Automation Workflow and IBM Process Mining.

When using IBM Process Mining to analyse BAW processes, process owners and analysts get a full objective picture of these processes: activities and transition frequencies, durations, costs, reworks, variants, and deviations. 

Process Mining helps understanding the business reasons that lead to non-optimal processes. Contextual data available in the process events are used to understand the root-causes, to mine the workflow business rules, and to create and monitor business KPIs in intuitive dashboards.

After having discovered the problems and having analyzed the root-causes, the analysts can plan for workflow improvements: automating a manual activity with a RPA bot, automating a business decision with business rules, changing the workflow, and so forth. 

With Process Mining, analysts can create what-if simulation scenarios in order to obtain instantly the ROI, the to-be KPIs.

## How to Use the Accelerator
This is a no-code accelerator that can be used by process owners and analysts who just need to fill-out a form to:
- Connect to the BAW server
- Select the BAW process to mine
- Optionnaly connect to the IPM server to automatically load the event log into a process mining project
- Optionnaly set an loop rate (in seconds) to extract new data regularly
- Optionnaly set an instance limit with a loop rate to fraction the extraction into smaller pieces and reduce the RAM and the impact on BAW.
- Optionnaly exclude some BAW data
- Run several extraction jobs that can be stopped and resumed.

## How to Install the Accelerator
Prerequisite: Python3 

Get this repository in your local environment

Go to the project directory, create a python virtual environment, activate the environment and install the packages.

```
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
pip install django
pip install requests
python manage.py migrate
```

The Web server is using Django. You need to generate a Django secret and to add it line 25 of ```execute_script/settings.py```.
You can generate a Django key from this site: https://djecrety.ir/


Contact Patrick Megard to get access to the libraries contained in this github repo:
https://github.com/Patrick-Megard/ibm-process-mining-connectors-utils

When you get access, download the zip file, and uncompress it.

You will obtain a folder called ```ibm-process-mining-connectors-utils-main```
Copy all the files that are in this folder into the ibm-process-mining-BAW-accelerator


## How to Run the Accelerator
When running a new shell you need to activate the virtual environment before executing the accelerator script:
```
source myenv/bin/activate
```

Run the accelerator:
```
python3 manage.py runserver
```

When the server is started, open a web browser and connect to your local host URL: `http://127.0.0.1:8000/`

Alternatively, when a configuration json file is saved, you can directly run the extraction by executing the python program
```
python3 BAW_to_IMP.py config/config_myJobName.json
```

## Configuring the extraction job
Each configuration requires a job name. The job name is used to identify the json configuration files and the CSV files.
For instance, if the job name is `myJobName`, the configuration file is saved in `config/config_myJobName.json`.<br>
The BAW event logs are saved in `data/BAW_myJobName_<timestamp>.zip` 

The Web UI enables:
- Creating a new extraction configuration 
- Editing an existing configuration
- Copying a new extraction configuration from an existing one (time saving)
- Loading an existing configuration file
- Deleting a configuration. Note that the json file is not deleted, the entry in the application DB is deleted.


## Running an extraction job
Before running an extraction job, you can set some running parameters
- Extraction loop rate defines the pause time between each extraction. You can enter a duration between 1 second and 24 hours. The JSON file enables entering any value as seconds. When the job includes a loop rate, the last extraction period is saved such that restarting the job does not extract the same data again.
- Number of threads increases the speed by splitting the extraction work into several threads. This increase the load on the BAW server too. A good balance needs to be found.
- Instance limit with loop_rate=0 is used for testing only: each extraction stops when the number of instance specified here is reached. This is useful when sizing the time required to get historical data, or the load on the BAW server or on the RAM
- Instance limit with loop_rate>=0 is used fraction the extraction steps in order to save RAM and to reduce impact on BAW. 
- Interval auto shift is used with a time interval [modified_after, modified_before], a loop rate, and optionally an instance_limit. The extraction starts with the initial interval, then shift the interval for another extraction. This can be useful to fragment the extraction when the data in the database is huge.
- Create a CSV at each loop generates a CSV file at each extraction loop (if events were retrieved). When unchecked, the CSV file is generated when the job is completed, stopped, or when the number of events reaches 500k events (the value can be changed in a code variable)

- A job can be stopped if it is looping. The stop is taken into consideration while the job is sleeping.
- Several jobs can be executed simultaneously.

Running a job without the WebUI is straightforward, and this way it can be scheduled using crontabs
```
python3 BAW_to_IMP.py config/config_myJobName.json
```
## Main extraction scenarios
The configuration directory includes several extraction examples for the main use cases
### Historical Basic
- Loop rate = 0
- instance limit = 0
- modified before = "2022-10-01T00:00:00Z"
- (optional) modified_after = "2022-09-01T00:00:00Z"
- (optional) number of threads = 5
- Interval auto shift = false
- Create CSV at each loop = false

The job is executed once and ends-up delivering a CSV file.

```CAUTIOUS```: the extraction can be very long. It can decrease the performance BAW and can request a huge RAM.
We recommend to use this only if you know that the extracted volume is reasonable.


### Historical Instance Limit
- Loop rate = 6 sec
- instance_limit = 50
- modified before = "2022-10-01T00:00:00Z"
- (optional) modified_after = "2022-11-21T00:00:00Z"
- (optional) number of threads = 5
- (optional) generate CSV at each loop = false
- Create CSV at each loop = false

During the first extraction loop, the job fetches all the instances that match the dates. But instead of getting the details of the tasks for each instance in one shot (this is the most consumming task), it get the task details for the first 50 instances, sleeps for 6 seconds, and continue getting the task details for the next 50 instance, and so forth until the instance list is completely processed.

Optionnaly we can generate a CSV file at each loop, and therefore keeping the RAM low. Without checking this option, a CSV file is generated each time we exceed 500k events (default). This threshold can be changed in the configuration file with 'event_number_csv_trigger'

This is the recommended approach for extracting historical data.

### Historical Interval Shifting
- Loop rate = 5 seconds
- modified before = "2022-10-01T00:00:00Z"
- modified after = "2022-09-01T00:00:00Z"
- instance_limit = 0
- (optional) number of threads = 5
- (optional) generate CSV at each loop = false
- Create CSV at each loop = false

This job starts extracting 1 month of data from modified after date (Sept 1, 2022), sleeps for 60 seconds, extracts the next month, and so forth until modified_before is reached.

This scenario is interesting to lower the impact on the RAM and on the BAW server. It is less predictable as the scenario that limits the number of instances. But it can be interesting to generate a CSV each day or each month.

It can be combined with an instance_limit

### Historical Interval Shifting Instance Limit
- Loop rate = 5 seconds
- modified before = "2022-10-01T00:00:00Z"
- modified after = "2022-09-01T00:00:00Z"
- instance_limit = 30
- (optional) number of threads = 5
- (optional) generate CSV at each loop = false
- Create CSV at each loop = false

Same as above, but each 'month' extraction is possibly fragmented in packs of 30 instances.

### Performance Sizing
- Loop rate = 0
- instance_limit = 1000
- (optional) modified before = "2022-10-01T00:00:00Z"
- (optional) modified after = "2022-09-01T00:00:00Z"
- (optional) number of threads = 5

The job extracts a maximum of 1000 instances as well as the task details. Then it generates the CSV.
We can't predict which instances are retrieved, therefore this is restricted to experimenting the performance before using another scenario 

### Monitor New Events
- Loop rate = 10 minutes
- generate CSV at each loop = true
- instance limit = 0
- modified after = "2022-11-21T00:00:00Z"
- (optional) number of threads = 5

The extraction job fetches new changes in BAW since "2022-11-21T00:00:00ZZ". If you first extracted historical data, the job kept the last extraction date in the field 'last before'. You should copy this date and use it as 'modified after' date for the near-real-time job.

Then the job sleeps for 10 minutes, and retry getting new events, and so forth.

A CSV file is generated at each loop. If a Process Mining configuration is set, the CSV is uploaded automatically such that new data is usable in process mining.


## Configuring the accelerator for BAW
The accelerator settings are managed in a form opened at `http://127.0.0.1:8000/bawjobs` 

You can use the accelerator to fetch the data from BAW and store the resulting CSV file in your local directory. You will then be able to load manually the CSV file into IBM Process Mining. In this case, you only need to have:
- IBM BAW admin login and password
- The process name (application) that you want to mine
- The project name to which the process belongs (acronym)

- You can enter the password in the Web UI or in the configuration file. But the password is visible in the configuration file
- You can store the password in an environment variable of your choice, and provide the environment variable name to the Web UI. This way, the password is not visible in the configuration file. <br>
Example from a linux shell:
```
export BAW_PASSWORD=myBAWPassword
```

The other BAW parameters are optional:

- Modified after: Retrieve process instances modified after the date expressed like this: 2022-06-01T22:07:33Z
- Modified before: Retrieve process instances modified before the date expressed like this: 2022-06-01T22:07:33Z

If you want to add specific process or task variables, you can list them in the "Business data" field of the job config file. Read the BAW data section below for more details

If the IBM Process Mining configuration left empty, the resulting CSV files will be loaded manually in IBM Process Mining.

In BAW, you can find the project name (acronym) in parenthesis besides the process name in <BAW_URL>/ProcessAdmin. 

See a screen shot of the BAW inspector at the bottom of this document

## Extracting the BAW business data
- Include exposed variables: If the process has declared exposed variables, these data can be automatically added to each event. The field name of each tracked data in the resulting CSV file starts with 'trkd'. Ex: trkd.requisition.requester. 

You can add any process or task data into the CSV. In the Web UI, list each data path separated with a comma (,). For example:

`requisition.requester,requisition.gmApproval,currentPosition.jobTitle,currentPosition.replacement.lastName`.

The field name for each variable in the resulting CSV file starts with 'tsk'. Ex: tsk.requisition.gmApproval

WARNING: a process mining project can only load CSV file with the same columns. If you add or remove a field during an extraction, you can't load it in an existing process mining project that loaded CSV files with different columns.

You can find these data in BAW process designer.

## Extracting the BAW process data
The configuration file `BAW_default_fields.json` can be modified to change the mapping between the BAW data and the default process mining fields, or to exclude more or less task common data. Copy the default file before modifying it.

You could change the mapping in :
```
  "process_mining_mapping": {
        "process_ID":"piid",
        "task_name":"name",
        "start_date":"startTime",
        "end_date":"completionTime",
        "owner":"owner",
        "team":"teamDisplayName"
    },
```

You could add task data that you don't need in this list, or keeping some by removing them from the list.
```
  "excluded_task_data": [
        "description",
        "clientTypes",
        "containmentContextID",
        "kind",
        "externalActivitySnapshotID",
        "serviceID",
        "serviceSnapshotID",
        "serviceType",
        "flowObjectID",
        "nextTaskId",
        "actions",
        "teamName",
        "teamID",
        "managerTeamName",
        "managerTeamID",
        "displayName",
        "processInstanceName",
        "assignedTo",
        "assignedToID",
        "collaboration",
        "activationTime",
        "lastModificationTime",
        "assignedToDisplayName",
        "closeByUserFullName"
    ]
```

The list of the default data is for reference only, it is not used by the program, but you can select from here data that you want to exclude.
```
    "included_task_data": [
        "activationTime",
        "atRiskTime",
        "completionTime",
        "description",
        "isAtRisk",
        "originator",
        "priority",
        "startTime",
        "state",
        "piid",
        "priorityName",
        "teamDisplayName",
        "managerTeamDisplayName",
        "tkiid",
        "name",
        "status",
        "owner",
        "assignedToDisplayName",
        "assignedToType",
        "dueTime",
        "closeByUser"
    ],
```

## Configuring the accelerator for IBM Process Mining

You can use the accelerator to fetch the data from BAW, and to automatically load the resulting CSV file into IBM Process Mining. The following parameters are required:
- IBM Process Mining
- User ID
- API Key
- Organization ID
- Project key

If the project key exists in the organization, the data is loaded into this project.<br>
If the project key does not exist yet, a new project is created with the same name.
Note= project keys can't include blank spaces. Use names like 'hiring-process'

In the IBM Process Mining User Profile, make sure you have API key enabled, and copy the API account and the API key.

See a screen shot of the Process Mining screen at the bottom of this document


## Configuration file
Instead of using the web server to configure an extraction job, you can create an edit configuration files. The configuration below results from the parameters entered with the Web UI.
Note how the BAW business data are implemented in JSON.

```
{
    "JOB": {
        "job_name": "CREATED",
        "exit": 0
    },
    "BAW": {
        "root_url": "http://baw.com/",
        "user": "admin",
        "password": "",
        "password_env_var": "BAW_ADMIN_PASSWORD",
        "project": "prj",
        "process_name": "process",
        "modified_after": "",
        "modified_before": "",
        "loop_rate": 0,
        "interval_shift": false,
        "thread_count": 1,
        "instance_limit": 0,
        "task_data_variables": [],
        "export_exposed_variables": false,
        "csv_at_each_loop": false,
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
```

## Screen shot to find connection parameters

![BAW inspector](./pictures/BAW_inspector.jpeg)

![IPM user profile](./pictures/IPM_userprofile.jpeg)




