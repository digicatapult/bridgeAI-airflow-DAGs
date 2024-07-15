# bridgeAI-airflow-DAGs

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following environment variables.

| Variable            | Default Value                      | Description                                                                                                                                   |
|---------------------|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| DATA_PATH           | None                               | File path to the raw data CSV data used for training. You may need to mount the and ensure the Pod has access to it.                          |
| MLFLOW_TRACKING_URI | `http://host.docker.internal:5000` | MLFlow tracking URI.                                                                                                                          |
| NAMESPACE           | None                               | Kubernetes cluster namespace                                                                                                                  |
| BASE_IMAGE          | None                               | Name of the model training image                                                                                                              |
| DOCKER_REG_SECRET   | None                               | Name of hte secret for the docker registry pull                                                                                               |
| CONFIG_MAP          | None                               | Name of the configmap containing the model training config                                                                                    |
| KUBECONFIG          | `~/.kube/config`                   | Path to the Kubeconfig file - [Reference](https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/stable/operators.html#id3) |

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

4. Open the Airflow web UI and trigger the DAG with name `model_training_dag`
