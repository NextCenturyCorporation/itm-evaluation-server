# In the Moment (ITM) - TA3 Server

This README provides a guide to set up and run the TA3 ITM server application.

## Prerequisites

Ensure you have Python 3.10 installed on your system. If you don't have it installed, you can download it from the [official Python website](https://www.python.org/downloads/).

## Setup

1. First, we need to setup a Python virtual environment. Navigate to the directory where you cloned the repository and run the following command to create a new virtual environment:

```
python -m venv venv
```

2. Activate the newly created virtual environment with:

```
source venv/bin/activate
```

On Windows, the method to activate depends on the shell:
- Git Bash: `source venv/Scripts/activate`
- PowerShell: `venv\Scripts\Activate.ps1`
- cmd.exe: `venv\Scripts\activate.bat`


## Configuration

Rename `config.ini.template` file to `config.ini`. The default values are for the production server, so you will probably want to change `SOARTECH_URL`, `ADEPT_URL`, `SAVE_HISTORY`, and `SAVE_HISTORY_TO_S3`.
See the template for likely values.

The following properties can be configured:
- `EVALUATION_TYPE` 
    - default is `phase1` but `dryrun` and `metrics` are also supported
- `SCENARIO_DIRECTORY`
    - default is `swagger_server/itm/data/%(EVALUATION_TYPE)s/scenarios/`
- `DEFAULT_DOMAIN`
    - default is `triage`
- `SUPPORTED_DOMAINS`
    - default is `triage`
- `SOARTECH_URL`
    - default is `http://10.216.38.25:8084`
- `ADEPT_URL`
    - default is `http://10.216.38.101:8080`
- `SAVE_HISTORY`
    - default is `True`
- `HISTORY_DIRECTORY`
    - default is `itm_history_output`
- `SAVE_HISTORY_TO_S3`
    - default is `True`
- `HISTORY_S3_BUCKET`
    - default is `itm-ui-assets`
- `ALL_TA1_NAMES`
    - default is `adept,soartech`
- A variety of ADEPT and SoarTech properties for filenames, scenario IDs, and alignment target IDs

*NOTE:* the trailing **`s`** in `.../data/%(EVALUATION_TYPE)s/...` is needed for string interpolation to work properly.

### Scenario filename convention
Scenario files must be named in the following format to be read by the server at runtime (without punctuation except the indicated hyphens).
This is the same convention used in the metrics evaluation:
- `<EVALUATION_TYPE>-<ta1name>-[eval|train]-<id>.yaml`

Please note:
1. `EVALUATION_TYPE` is the value of the configuration variable defined in `config.ini`;
2. `ta1name` is either `soartech` or `adept`;
3. Use `eval` for evaluation scenarios and `train` for training scenarios; and
4. The `id` should be derived from the scenario ID in the YAML file, although it isn't required, e.g., `qol`, `MJ2`, `urban`, etc.


## Installation and Usage

### Installation
Once setup and configuration are complete, to install the server, simply run:
```
pip3 install -r requirements.txt
```

### Running from the command line
To run the server, please execute from the root directory with the following usage:
```
usage: python -m swagger_server [-h] [-t] [-c CONFIG_GROUP] [-p PORT]

options:
  -h, --help            show this help message and exit
  -c CONFIG_GROUP, --config_group CONFIG_GROUP
                        Specify the configuration group in `config.ini` used to launch the Swagger server (default = DEFAULT)
  -p PORT, --port PORT  Specify the port the Swagger server will listen on (default = 8080)
  -t, --testing         Put the server in test mode which will run standalone and not connect to TA1.
```

You can browse the API at:

```
http://localhost:8080/ui/
```

Your Swagger definition lives here:

```
http://localhost:8080/swagger.json
```

To launch the integration tests, use tox:
```
sudo pip install tox
tox
```

### Running with Docker

To run the server on a Docker container, please execute the following from the root directory:

```bash
# building the image
docker build -t swagger_server .

# starting up a container
docker run -p 8080:8080 swagger_server
```

### Running with docker on separate instances
To run with TA1 on multiple systems set docker env vars for ADM host, Soartech Host, and ADEPT Host.
```bash
docker run -d -p 8080:8080 --name itm-server itm-server
```
** Note, If setting `TA3_PORT` to anything other then the default requires the docker run command to expose those ports. 
Can write the above command as `$TA3_PORT:$TA3_PORT` however, this will not work if it is not set and won't default.

### Manual runs on separate instances
If running the command instead of docker set the environment variables for:
- `TA3_PORT` (default:8080)

## Updating models
This requires JDK 8 or higher to run the gradle tool.

The models in swagger_server/models are generated from the following file:
* `swagger/swagger.yaml`

If this file is updated it will need to be re-generated and checked in.
Run `./gradlew` to do this.

**NOTE**: When you regenerate models, this will remove the allowed enum values in `action_type_enum.py`, `character_role_enum.py`, and `threat_type_enum.py`.  If you make changes to these model objects (presumably by adding enums), you'll need to undo the generated changes and add your new enum values manually.  See [this OpenAPI issue](https://github.com/OAI/OpenAPI-Specification/issues/1552) for background info.

## Adding a domain
To add a domain, you'll need to:
1. Update the YAML definition of certain domain-specific versions of the model and define nested state;
2. Implement a domain-specific version of certain ITM server classes;
3. Create domain-specific tests;
4. Create and update configuration; and
5. Document your domain actions in the `itm-client-evaluation` repository.

### Update YAML definition
Modify the definitions of the domain-specific versions of various state objects (i.e., the model), namely:
- `DomainState`: high-level, domain-specific state relevant to a scenario or a scene therein
- `DomainCharacter`: domain-specific attributes of the characters in the scenario
- `DomainDemographics`: domain-specific demographic attributes of the characters in the scenario
- `DomainConditions` domain-specific conditions that specify whether to transition to the next scene or send a probe response
- `DomainThreatTypeEnum`: domain-specific type or nature of the risk or threat to the characters in the sceanrio, or to the decision-maker
- `DomainCharacterRoleEnum`: domain-specific primary roles a character may have in the scene
- `DomainActionTypeEnum`: domain-specific (string) action types supported in the server
- `EntityTypeEnum`: domain-specific enumeration of available entity types; can be a subject or object of a `MESSAGE` action

Add YAML definitions for any nested objects defined in the above state objects.  If any other model objects require domain-specific content, then create both a `Base` and `Domain` version of each object, and change the current object to include both of these versions with the `allOf` keyword. This may also entail other server code changes.  All YAML changes should be made to the `swagger/swagger.yaml` file, and used by your client ADM.  Note that the hope is to move all domain-specific state to a separate file, but this isn't supported cross-platform with our current dependencies.

### Implement domain-specific classes
Create a directory, `swagger_server/itm/domains/<domainname>`, and implement the following classes:
- `<Domain>Config`, which implements the `ITMDomainConfig` protocol, which defines factory-like methods for creating domain objects
- `<Domain>ActionHandler` (a subclass of `ITMActionHandler`), with:
   - `validate_domain_action` for validating domain-specific actions
   - `process_domain_action` for the core business logic of handling a domain-specific action
   - `load_action_times`: for loading a mapping of domain-specific action types and simulated elapsed time for processing the action
- `<Domain>Scenario` (a subclass of `ITMScenario`), with:
   - `merge_state` for merging domain-specific state from a new scene into the current state
   - `clear_hidden_data` in case any state data should be hidden at scene start
- `<Domain>ScenarioReader` (a subclass of `ITMScenarioReader`), with the methods `generate_state`, `convert_to_itmscene`, and, if there are any domain-specific conditions, `generate_conditions`
- `<Domain>Scene` (a subclass of `ITMScene`), with:
   - `evaluate_domain_conditions` if there are any domain-specific conditions
   - `get_valid_action_types` if there are conditions where non-restricted domain-specific actions should NOT be added as available actions

### Create domain-specific tests
Create a directory, `swagger_server/itm/data/domains/<domainname>/test` and add domain-specific tests, and/or domain-specific variants of existing tests.

### Create and update configuration
Make the following changes to configuration (`config.ini.template`, replicated in `config.ini`):
- Create a file, `<domainname>ActionTimes.json>` in `swagger_server/itm/data/domains/<domainname>/` with a dictionary of domain-specific action types and simulated time (in seconds) for a given action to be performed.
- Update the `SUPPORTED_DOMAINS` and (if desired) `DEFAULT_DOMAIN` keywords in `config.ini.template` and `config.ini` at the root level.

### Document your domain
You should document your domain for multiple audiences, including scenario writers and TA2 ADMs. Some suggestions:
- In the [TA3 client repository](https://github.com/NextCenturyCorporation/itm-evaluation-client), create a new file at the root level, `README-<domainname>.md`, a Markdown file with a description of domain-specific actions and FAQs.  The audience is primarily ADM writers.
- Consider writing a document [like this](https://nextcentury.atlassian.net/wiki/spaces/ITMC/pages/3041951763/Scenario+YAML+Documentation) that documents every property in the domain-specific state, including controlled vocabulary, data type, and how to use each field.
- If the domain uses a wide variety of controlled vocabulary, consider writing [a glossary](https://nextcentury.atlassian.net/wiki/download/attachments/3041951763/ITM%20Scenario%20Glossary%20(Phase%201%20Final).pdf?api=v2) that documents each property and possible value.

## Adding a TA1
To add a TA1, you'll need to create and update configuration and implement a domain-specific version of certain ITM server classes.
You'll also have to update the [TA3 client repository](https://github.com/NextCenturyCorporation/itm-evaluation-client) if you want to
be able to use its sample clients.  See its README for details.

### Create and update configuration
Make the following changes to configuration (`config.ini.template`, replicated in `config.ini`):
- Add a new all-lowercase ta1 name to `ALL_TA1_NAMES`.
- Define the following variables in both the `DEFAULT` and `GROUP_TARGET` configuration groups:
  - `<TA1>_EVAL_FILENAMES`, `<TA1>_TRAIN_FILENAMES`
  - For each KDMA, define `<TA1>_EVAL_<KDMA>_SCENARIOS`, `<TA1>_TRAIN_<KDMA>_SCENARIOS`, and `<TA1>_<KDMA>_ALIGNMENT_TARGETS`.

### Implement domain-specific classes
In the directory `swagger_server/itm/ta1`, create a child class `<TA1name>Ta1Controller` of `ITMTa1Controller`, and implement all abstract methods (e.g., `get_ta1name`, `get_alignment_ids_path`, and `new_session`, among others).  Override any `ITMTa1Controller` methods as necessary.
Add code to get the configuration values defined above (see current TA1 controllers for examples).  Depending how extensive/different your TA1 server is from current cases, you may need to make changes to `ITMTa1Controller`.