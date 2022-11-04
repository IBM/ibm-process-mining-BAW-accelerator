# Accelerator for IBM Business Automation Workflow and IBM Process Mining
## NOTE
To obtain the librairies required to execute the accelerator, please contact Patrick Megard (patrick.megard@fr.ibm.com).

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
- Optionnaly set an udate rate (in seconds) to extract new data regularly
- Optionnaly set an extraction period in days to fraction the extraction workload
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
pip install pandas
python manage.py migrate
```

The Web server is using Django. You need to generate a Django secret and to add it line 25 of ```execute_script/settings.py```.
You can generate a Django key from this site: https://djecrety.ir/


Contact Patrick Megard to get access to the libraries contained in this github repo:
https://github.com/Patrick-Megard/ibm-process-mining-connectors-utilsWhen you get access, download the zip file, and uncompress it.

You will obtain a folder called ```ibm-process-mining-connectors-utils-main```
Copy all the files that are in this folder into the ibm-process-mining-BAW-accelerator


## How to Run the Accelerator
When running a new shell you need to activate the virtual environment before executing the accelerator script:
```
source myenv/bin/activate
```

Run the accelerator:
```
python manage.py runserver
```

When the server is started, open a web browser and connect to your local host URL: `http://127.0.0.1:8000/`

## Configuring the extraction job
Each configuration requires a job name. The job name is used to identify the json configuration files and the CSV files.
For instance, if the job name is `myJobName`, the configuration file is saved in `config/config_myJobName.json`.<br>
The BAW event logs are saved in `data/BAW_myJobName_<timestamp>.zip` 

When an extraction configuration is started with the button 'Start extraction', the configuration file is automatically saved. 
- Running extraction jobs can be stopped by clicking 'Stop extraction' button.
- By just providing the job name and clicking 'Resume extraction' button, you can restart an extraction without having to fill-out all the form. You can change the update rate.
- Alternatively, you can launch the extraction program from a shell: `python3 BAW_to_IMP.py config/config_myJobName.json`

You can run several jobs simultaneously. The program executes a new python program as a subprocess each time you click the 'Start extraction' button. At any moment you can stop a job, or restart a job, providing that the corresponding configuration exists in config/.

### Extraction loop rate and extraction interval
- Extraction loop rate defines the pause time between each extraction. The UI proposed pre-defined choices as seconds, minutes, and hours. The JSON file enables entering any value as seconds. When the job includes a loop rate, the last extraction period is saved such that restarting the job does not extract the same data again.
- Extraction interval is expressed as days. This value specifies a time window for which we want to extract BAW data. For example if the extraction interval is 1 day, at each loop we will extract 1 day of data, and the time window is shifted for the next loop. An extraction loop rate and a modified_after date are required to use this feature.


## Configuring the accelerator for BAW
The accelerator settings are managed in a form opened at `http://127.0.0.1:8000/`

You can use the accelerator to fetch the data from BAW and store the resulting CSV file in your local directory. You will then be able to load manually the CSV file into IBM Process Mining. In this case, you only need to have:
- IBM BAW admin login and password
- The process name (application) that you want to mine
- The project name to which the process belongs (acronym)

The other BAW parameters are optional:
- Number of threads: used to balance the extraction process on several threads. Keep empty if the extraction seems to occur in a reasonable time
- Number of instances: limit the number of instances extracted
- Modified after: Retrieve process instances modified after the date expressed like this: 2022-06-01T22:07:33Z
- Modified before: Retrieve process instances modified before the date expressed like this: 2022-06-01T22:07:33Z

If you want to add specific process or task variables, you can list them in the "Business data" field of the job config file. Read the BAW data section below for more details

If the IBM Process Mining configuration left empty, the resulting CSV files will be loaded manually in IBM Process Mining.

In BAW, you can find the project name (acronym) in parenthesis besides the process name in <BAW_URL>/ProcessAdmin. 

See a screen shot of the BAW inspector at the bottom of this document

## Extracting the BAW business data
If the process has declared tracked data, these data are automatically added to each event. The field name of each tracked data in the resulting CSV file starts with 'trkd'. Ex: trkd.requisition.requester

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

To create a new project and upload the data:
- Project name

To upload the data into an existing project:
- Project key

In the IBM Process Mining User Profile, make sure you have API key enabled, and copy the API account and the API key.

See a screen shot of the Process Mining screen at the bottom of this document

![BAW-IPM-Connection](./pictures/BAW_IPM_WebUI.jpeg)


## Configuration file
Instead of using the web server to configure an extraction job, you can create an edit configuration files. The configuration below results from the parameters entered in the previous form.
Note how the BAW business data are implemented in JSON.

```
{
    "JOB": {
        "job_name": "test",
        "update_rate": 60,
        "exit": 0
    },
        "BAW": {
        "root_url": "BAW.com",
        "user": "admin",
        "password": "admin",
        "project": "HSS",
        "process_name": "Standard HR Open New Position",
        "modified_after": "2021-10-01T00:00:00Z",
        "modified_before": "",
        "extraction_interval": 5,
        "thread_count": 1,
        "instance_limit": -1,
        "task_data_variables": [
            "requisition.requester",
            "requisition.gmApproval",
            "currentPosition.jobTitle",
            "currentPosition.replacement.lastName"
        ],
        "last_after": "",
        "last_before": ""
    },
    "IPM": {
        "url": "https://IPM.com",
        "user_id": "user.name",
        "api_key": "2345",
        "org_key": "567890",
        "project_key": "my-project",
        "project_name": ""
    }
}
```

We recommend that configuration files are stored in the directory congif/, and that the configuration file name complies with the following conventions: config_<job_name>.json. Then you can start/resume the job using the web server UI.

Alternatively you can execute each job using the following command:
```
python3 NearRealTimeUpdates.py config_<job_name>.json
```

## Screen shot to find connection parameters

![BAW inspector](./pictures/BAW_inspector.jpeg)

![IPM user profile](./pictures/IPM_userprofile.jpeg)




