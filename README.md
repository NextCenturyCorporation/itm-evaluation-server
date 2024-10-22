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

Rename `config.ini.template` file to `config.ini`. The default values are for the production server, so you
will probably want to change `SOARTECH_URL`, `ADEPT_URL`, `SAVE_HISTORY`, and `SAVE_HISTORY_TO_S3`.
See the template for likely values.

The following properties can be configured:
- `EVALUATION_TYPE` 
    - default is `dryrun` but `metrics` is also supported
- `SCENARIO_DIRECTORY`
    - default is `swagger_server/itm/data/%(EVALUATION_TYPE)s/scenarios/`
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

## Usage
To run the server, please execute the following from the root directory:

```
pip3 install -r requirements.txt
python -m swagger_server
```

### Installation and Usage
To run the server, please execute from the root directory with the following usage:
```
usage: python -m swagger_server [-h] [-c CONFIG_GROUP] [-p PORT]

Specify Config Group, will default to the DEFAULT group

options:
  -h, --help            show this help message and exit
  -c CONFIG_GROUP, --config_group CONFIG_GROUP
                        Specify the configuration group in config.ini used to launch the Swagger server (default = DEFAULT)
  -p PORT, --port PORT  Specify the port the Swagger server will listen on (default = 8080)
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

## Running with Docker

To run the server on a Docker container, please execute the following from the root directory:

```bash
# building the image
docker build -t swagger_server .

# starting up a container
docker run -p 8080:8080 swagger_server
```

## Running with docker on separate instances
To run with TA1 on multiple systems set docker env vars for ADM host, Soartech Host, and ADEPT Host.
```bash
docker run -d -p 8080:8080 --name itm-server itm-server
```
** Note, If setting TA3_PORT to anything other then the default requires the docker run command to expose those ports. 
Can write the above command as $TA3_PORT:$TA3_PORT however, this will not work if it is not set and won't default.

## Manual runs on separate instances
If running the command instead of docker set the environment variables for:
- TA3_PORT (default:8080)

## Updating models
This requires JDK 8 or higher to run the gradle tool.

The models in swagger_server/models are generated from the following files
    swagger_server/swagger/swagger.yaml
    swagger_server/swagger/ta1.yaml
If these files are updated they will need to be re-generated and checked in.
Run `./gradlew` to do this.
