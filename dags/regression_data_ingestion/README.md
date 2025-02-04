# Regression model Data Ingestion DAG

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following [Airflow variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html). Refer to the [Notes](#notes) for details.

| Variable                    | Default Value                                                  | Description                                                                                                                                                                                                                                                                                                                                                 |
|-----------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| data_url                    | None                                                           | Data url of the csv file. You should be able to access the file via `curl`                                                                                                                                                                                                                                                                                  |
| namespace                   | `airflow`                                                      | Kubernetes cluster namespace                                                                                                                                                                                                                                                                                                                                |
| base_image_data_ingestion   | `digicatapult/bridgeai-regression-model-data-ingestion:latest` | Name of the data ingestion image                                                                                                                                                                                                                                                                                                                            |
| is_base_image_authenticated | `False`                                                        | Is the base image `base_image_data_ingestion` needs authentication to pull?                                                                                                                                                                                                                                                                                 |
| docker_reg_secret           | `ghcr-io`                                                      | Name of the secret for the docker registry pull if `is_base_image_authenticated` is `True`                                                                                                                                                                                                                                                                  |
| data_ingestion_configmap    | `data-ingest-configmap`                                        | Name of the configmap containing the data ingestion config                                                                                                                                                                                                                                                                                                  |
| connection_id               | `local-k8s`                                                    | Kubernetes connection id                                                                                                                                                                                                                                                                                                                                    |
| in_cluster                  | `True`                                                         | Run kubernetes client with in_cluster configuration                                                                                                                                                                                                                                                                                                         |
| github_secret               | `github-auth`                                                  | Name of the secret for git access                                                                                                                                                                                                                                                                                                                           |
| github_secret_username_key  | `username`                                                     | Key corresponding to the git username in the above github_secret                                                                                                                                                                                                                                                                                            |
| github_secret_password_key  | `password`                                                     | Key corresponding to the git password in the above github_secret                                                                                                                                                                                                                                                                                            |
| data_ingestion_pvc          | `data-ingestion-pvc`                                           | The name of the PVC assigned for data ingestion DAG                                                                                                                                                                                                                                                                                                         |
| dvc_remote                  | "s3://artifacts"                                               | dvc remote                                                                                                                                                                                                                                                                                                                                                  |
| dvc_remote_name             | "regression-model-remote"                                      | name for dvc remote                                                                                                                                                                                                                                                                                                                                         |
| aws_conn_name               | "aws_default"                                                  | an AWS connection created with connection type: 'AWS Web Services', and an optional 'AWS Access Key ID' and 'AWS Secret Access Key' (not needed when using IAM based access to dvc remote).                                                                                                                                                                 |
| dvc_endpoint_url            | `http://minio`                                                 | The URL endpoint for the DVC storage backend. This is typically the URL of an S3-compatible service, such as MinIO                                                                                                                                                                                                                                          |
| deploy_as_code              | `False`                                                        | Whether to use deploy as code approach or deploy as model approach. With deploy as code, a manual trigger of this data ingestion DAG automatically launches the subsequent DAG for model training on the latest data. The newly trained model is then assumed to be superior and is deployed without further approval, unlike the deploy as model approach. |


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

4. Open the Airflow web UI and trigger the DAG with name `data_ingestion_dag`

New data will be available in the specified repo's specified branch with a tag prefix `data-` followed by version.

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
`bridgeAI-regression-model-data-ingestion` repo.*\
To verify the config,
```shell
kubectl describe configmap data-ingestion-config --namespace=bridgeai
````
### Creating a PVC within the kubernetes namespace
Create a file named data-ingestion-pvc.yaml with the following contents
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-ingestion-pvc
  namespace: bridgeai
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

```
Then apply this yaml to create the PVC
```shell
kubectl apply -f data-ingestion-pvc.yaml
```
Check the volume status
```shell
kubectl get pvc -n bridgeai
```

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
                path="/app/data",
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

