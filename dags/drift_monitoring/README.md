# Drift monitoring DAG

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following [Airflow variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html). Refer to the [Notes](#notes) for details.

| Variable                    | Default Value                                                                  | Description                                                                                      |
|-----------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| namespace                   | `airflow`                                                                      | Kubernetes cluster namespace                                                                     |
| base_image_drift_monitoring | `digicatapult/bridgeai-drift-monitoring:latest`                                | Name of the model training image                                                                 |
| is_base_image_authenticated | `False`                                                                        | Is the base image `base_image_drift_monitoring` needs authentication to pull?                    |
| docker_reg_secret           | `ghcr-io`                                                                      | Name of the secret for the docker registry pull if `is_base_image_authenticated` is `True`       |
| drift_monitoring_configmap  | `drift-monitoring-configmap`                                                   | Name of the configmap containing the model training config                                       |
| connection_id               | `local-k8s`                                                                    | Kubernetes connection id                                                                         |
| in_cluster                  | `True`                                                                         | run kubernetes client with in_cluster configuration                                              |
| dvc_remote                  | `s3://artifacts`                                                               | dvc remote                                                                                       |
| dvc_endpoint_url            | `http://minio`                                                                 | dvc endpoint url                                                                                 |
| dvc_access_key_id           | `admin`                                                                        | access key for dvc remote                                                                        |
| dvc_secret_access_key       | `password`                                                                     | secret access key for dvc remote                                                                 |
| github_secret               | `github-auth`                                                                  | Name of the secret for git access                                                                |
| github_secret_username_key  | `username`                                                                     | Key corresponding to the git username in the above github_secret                                 |
| github_secret_password_key  | `password`                                                                     | Key corresponding to the git password in the above github_secret                                 |
| log_level                   | `INFO`                                                                         | log level                                                                                        |
| data_repo                   | `https://github.com/digicatapult/bridgeAI-regression-model-data-ingestion.git` | data ingestion repo where the data is versioned with dvc                                         |
| historical_data_version     | `data-v1.0.0`                                                                  | the data version (dvc tagged version from the data ingestion repo) used for training the model   |
| new_data_version            | `data-v1.1.0`                                                                  | the data version (dvc tagged version from the data ingestion repo) curresponding to the new data |
| model_endpoint              | `http://host.docker.internal:5001/invocations`                                 | deployed model endpoint using which predictions can be made                                      |
| drift_monitoring_pvc        | `drift_monitoring_pvc`                                                         | PVC claim name for this dag                                                                      |


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

4. Open the Airflow web UI and trigger the DAG with name `drift_monitoring_dag`

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
