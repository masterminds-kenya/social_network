# social_network

**Author**: Chris L Chapman
**Version**: 0.0.1

## Deployment

We are currently deploying on google cloud (gcloud), with a flask server. Gcloud is expecting a pip requirements file (requirements.txt), an app.yaml file (indicating what python version to use), and a main.py file for our server code file. Gcloud also allows an ignore file (.gcloudignore) which follows the same concepts from .gitignore files. Locally we are using pipenv to help us track dependencies and packages only needed in the development environment. However, the Pipfile and Pipfile.lock files should be in the ignore file for uploading to gcloud.

## Development notes

We are expecting an `.env` file at the root of the project so the `config.py` works correctly. For deployment, we also need to update the `app.yaml` file with the appropriate environment variables.

When running locally, we can proxy the database. This requires a cloud_sql_proxy file, and knowing the DB_CONNECTION_NAME. In the terminal, substituting as needed, execute the following command:

``` bash*
./cloud_sql_proxy -instances="DB_CONNECTION_NAME"=tcp:3306
```
