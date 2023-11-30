# Web-Service-Python

## Description

This a simple python web service that uses the Fastapi framework to create a RESTful API as well as a webserver. This is meant to be used as a template for future projects.The project includes a fully dockerised environment with a docker-compose file to run the project. The project also includes postgresql database and a redis database. There is RQ worker support for asyncronous tasks. The included Minio server is used for file storage. The frontend is through the Jinja2 templating engine. It also includes Nginx and certbot for SSL support.
## Includes
- [x] Fastapi
- [x] Jinja2
- [x] Postgresql
- [x] Redis
- [x] Celery
- [x] Minio
- [x] Nginx
- [x] Certbot
- [x] Support for private python packages from private repositories
- [x] Ruff
- [x] Github actions for CI/CD
- [x] Makefile for easy setup
- [x] VS Code Debugger support through debugpy

## Installation

### Docker

1. Install Docker and Docker-compose
2.Copy the .env-copy file to .env and fill in the variables
1. If the docker requires access to a private repository you need to load your ssh key to your ssh-agent using `ssh-add` command.

   ```bash
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/<your-ssh-key> #set the path to your ssh key
    ```

2. Build the docker compose file

```bash
docker-compose build
```

4. Run the docker compose file

```bash
docker-compose up
```

5. The webserver should be running on localhost on the port defined in the .env file
6. Create a bucket in the minio server with the name defined in the .env file
7. The project uses alemic to manage the database. To create the database run the following command

```bash
alemic upgrade head
```

### Use makefile

1. Install Docker and Docker-compose
2. Copy the .env-copy file to .env and fill in the variables
3.If the docker requires access to a private repository you need to load your ssh key to your ssh-agent using `ssh-add` command.
   ```bash
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/<your-ssh-key> #set the path to your ssh key
    ```

4. Run the makefile

```bash
make init
```

5. The webserver should be running on localhost on the port defined in the .env file

## Development

The project uses poetry to manage the python dependencies.

### Prerequisites

- `Poetry` (version equal to `1.7.0`) [Installation Guide](https://python-poetry.org/docs/#installation)
- `Python 3.10`
- `Docker` (Optional)
- `docker-compose` (Optional)

### Add new packages

- `poetry add package-name=version-number`
- Dev dependencies can be added using `--group dev` flag.

### Remove package

- `poetry remove package-name`

### Locking dependencies

- `poetry lock`
  - This will update `poetry.lock` file with latest versions of all dependencies.
  - This should be done before committing changes to `pyproject.toml` file.

### Update dependencies

- `poetry update`
  - This will update all dependencies to latest version.
  - This will also update `poetry.lock` file.
- `poetry update package-name`
  - This will update `package-name` to latest version.
  - This will also update `poetry.lock` file.
- `poetry add <package-name@latest>  --group dev`
  - This will update `package-name` for `dev` group as there is no straight forward way yot update dev dependencies to latest version.
  - Remember to pin dependency in this case.
  - This will also update `poetry.lock` file.

### Setting up pre-commit

This is used for running lint rules before committing changes to the repo. `pre-commit` command should be installed as
part of installing dependencies. To check if it is working properly, run `pre-commit --version`, you should see `3.5.0`
or newer version.

- To install git commit hooks, run `pre-commit install`. And you're done.
- For more information, refer [here](https://pre-commit.com/)

### Using alembic

To create a new migration run the following command

```bash
alembic revision --autogenerate -m "migration message"
```

To apply the migration run the following command

```bash
alembic upgrade head
```

To downgrade the migration run the following command

```bash
alembic downgrade -1
```

### Using VS Code Debugger
1. Install the python extension for VS Code.
2. Use the included `launch.json` file to run the debugger.
3. Use the custom docker compose file to run the debugger.
```bash
docker-compose -f docker-compose.debug.yml up
```
4. Set breakpoints in the code and run the debugger vs code(Wait for debugpy to be installed).
5. The debugger should be running on port 5678.

### Other editors
Comment out the `debugpy` `start-debug.sh` file and run the docker compose file above.

### Setting up nginx and certbot

1. Modify configuration in `nginx/app.conf`, `init_cert.sh` with the appropriate config/credentials.

2. Run the init script(Ensure that you have made the appropriate dns mapping for the server at your domain provider):

```bash
./init_cert.sh
```
