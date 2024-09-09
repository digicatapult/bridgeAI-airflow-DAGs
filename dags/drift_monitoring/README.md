# Drift monitoring DAG

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following [Airflow variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html). Refer to the [Notes](#notes) for details.

| Variable                   | Default Value                                  | Description                                                                                      |
|----------------------------|------------------------------------------------|--------------------------------------------------------------------------------------------------|
| namespace                  | None                                           | Kubernetes cluster namespace                                                                     |
| base_image                 | None                                           | Name of the model training image                                                                 |
| docker_reg_secret          | None                                           | Name of the secret for the docker registry pull                                                  |
| config_map                 | None                                           | Name of the configmap containing the model training config                                       |
| connection_id              | None                                           | Kubernetes connection id                                                                         |
| in_cluster                 | False                                          | run kubernetes client with in_cluster configuration                                              |
| dvc_remote                 | `s3://artifacts`                               | dvc remote                                                                                       |
| dvc_endpoint_url           | `http://minio`                                 | dvc endpoint url                                                                                 |
| dvc_access_key_id          | `admin`                                        | access key for dvc remote                                                                        |
| dvc_secret_access_key      | `password`                                     | secret access key for dvc remote                                                                 |
| github_secret              | `github-auth`                                  | Name of the secret for git access                                                                |
| github_secret_username_key | `username`                                     | Key corresponding to the git username in the above github_secret                                 |
| github_secret_password_key | `password`                                     | Key corresponding to the git password in the above github_secret                                 |
| log_level                  | `INFO`                                         | log level                                                                                        |
| data_repo                  | None                                           | data ingestion repo where the data is versioned with dvc                                         |
| historical_data_version    | `data-v1.0.0`                                  | the data version (dvc tagged version from the data ingestion repo) used for training the model   |
| new_data_version           | `data-v1.1.0`                                  | the data version (dvc tagged version from the data ingestion repo) curresponding to the new data |
| model_endpoint             | `http://host.docker.internal:5001/invocations` | deployed model endpoint using which predictions can be made                                      |
| drift_monitoring_pvc       | `drift_monitoring_pvc`                         | PVC claim name for this dag                                                                      |


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

### Mounting host path to a container generated using KubernetesPodOperator 

If using a KIND cluster, to mount a host path to the model training container;
1. Mount the host local path to the kind cluster
    a) Create a `kind-config.yaml` file with the following content
    ```yaml
    kind: Cluster
    apiVersion: kind.x-k8s.io/v1alpha4
    nodes:
      - role: control-plane
        extraMounts:
          - hostPath: /host/local/directory/tobe/mounted
            containerPath: /mnt/data  # path name for the cluster
    ```
    b) Create a kind cluster with the created config
    ```shell
   kind create cluster --name bridgeai --config kind-config.yaml
    ```
2. Mount the cluster mount point path to the container in the python dag code within `KubernetesPodOperator`
    a) create volume
    ```python
    volumes=[
        k8s.V1Volume(
            name="host-data-volume",
            host_path=k8s.V1HostPathVolumeSource(
                path="/mnt/data",
                type="Directory"
            )
        ]
    ```
    b)  use the volume mount
    ```python
    volume_mounts=[
        k8s.V1VolumeMount(
            name="host-data-volume",
            mount_path="/app/artefacts",
            read_only=False,
            )
        ]
    ```
