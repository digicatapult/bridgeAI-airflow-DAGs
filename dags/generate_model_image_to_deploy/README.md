# Generate model base image to deploy DAG

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following [Airflow variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html). Refer to the [Notes](#notes) for details.

| Variable                    | Default Value                 | Description                                                 |
|-----------------------------|-------------------------------|-------------------------------------------------------------|
| namespace                   | None                          | Kubernetes cluster namespace                                |
| base_image                  | None                          | Name of the model training image                            |
| docker_reg_secret           | None                          | Name of the secret for the docker registry pull             |
| config_map                  | None                          | Name of the configmap containing the model training config  |
| connection_id               | None                          | Kubernetes connection id                                    |
| in_cluster                  | False                         | run kubernetes client with in_cluster configuration         |
| mlflow_tracking_uri         | `http://localhost:8080`       | The URI for the MLflow tracking server                      |
| deploy_model_name           | `house_price_prediction_prod` | The name of the model to be deployed                        |
| deploy_model_alias          | `champion`                    | The alias for the deployed model                            |
| docker_registry             | `localhost:5000`              | The Docker registry where images are stored                 |
| mlflow_built_image_name     | `mlflow_model`                | The name of the MLflow model Docker image                   |
| mlflow_built_image_tag      | `latest`                      | The tag for the MLflow model Docker image                   |


3. Add the absolute path to `./dags` directory of this repo to the Airflow dags path using one of the method\
    a. Using the `airflow.cfg` file - Update the `dags_folder`
    ```yaml
    [core]
    # The folder where your airflow pipelines live, most likely a
    # subfolder in a code repository. This path must be absolute.
    #
    # Variable: AIRFLOW__CORE__DAGS_FOLDER
    #
    dags_folder = /app/bridgeAI-airflow-DAGs/dags
    ```
    b. Set the environment variable - `AIRFLOW__CORE__DAGS_FOLDER`

    c. *Note: [This](https://airflow.apache.org/docs/helm-chart/stable/manage-dags-files.html#mounting-dags-using-git-sync-sidecar-with-persistence-enabled) could be a better approach for syncing the DAGs directory for deployment.*

4. Open the Airflow web UI and trigger the DAG with name `create_model_image_to_deploy`

---
## Notes:

### Creating docker registry secret
To create a docker registry secret named "docker-registry-secret" to set the variable `docker_reg_secret`;\
```shell
kubectl create secret docker-registry docker-registry-secret \
  --docker-username=<docker-username> \
  --docker-password=<docker-password> \
  --docker-email=<docker-email> \
  --docker-server=<docker-server> \
  --namespace=bridgeai
```
### Creating configmap
To create a configmap from a yaml file, run the following\
```shell
kubectl create configmap training-config --from-file=config.yaml --namespace=bridgeai
```
*The current `config.yaml` file can be directly taken form the
`bridgeAI-regression-model-training` repo.*\
To verify the config,
```shell
kubectl describe configmap training-config --namespace=bridgeai
````