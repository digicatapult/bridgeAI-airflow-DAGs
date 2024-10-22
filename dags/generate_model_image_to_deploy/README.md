# Generate model base image to deploy DAG

The generated model base image will be pushed to ECR.

# How to:
1. Install the dependencies in the container where Airflow is running\
    `pip install airflow`\
    `pip install apache-airflow-providers-cncf-kubernetes`
2. Set the following [Airflow variables](https://airflow.apache.org/docs/apache-airflow/stable/howto/variable.html). Refer to the [Notes](#notes) for details.

| Variable                                 | Default Value                                    | Description                                                                                                                                                       |
|------------------------------------------|--------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| namespace                                | `airflow`                                        | Kubernetes cluster namespace                                                                                                                                      |
| base_image_model_image_generation        | `digicatapult/bridgeai-model-baseimage:latest`   | Name of the model training image                                                                                                                                  |
| is_base_image_authenticated              | `False`                                          | Is the base image `base_image_model_image_generation` needs authentication to pull?                                                                               |
| docker_reg_secret                        | `ghcr-io`                                        | Name of the secret for the docker registry pull if `is_base_image_authenticated` is `True`                                                                        |
| connection_id                            | `local-k8s`                                      | Kubernetes connection id                                                                                                                                          |
| in_cluster                               | `True`                                           | run kubernetes client with in_cluster configuration                                                                                                               |
| mlflow_tracking_uri                      | `https://mlflow.dc-mlops.co.uk`                  | The URI for the MLFlow tracking server. Use `http://mlflow-tracking:80` for kind cluster.                                                                         |
| mlflow_tracking_username                 | None                                             | MLFlow tracking username. In kind cluster no need to set it as there is no authentication needed, but ensure that you set it on Production cluster.               | 
| mlflow_tracking_password                 | None                                             | MLFlow tracking password. In kind cluster no need to set it as there is no authentication needed, but ensure that you set it on Production cluster.               |
| deploy_model_name                        | `house_price_prediction_prod`                    | The name of the model to be deployed                                                                                                                              |
| deploy_model_alias                       | `champion`                                       | The alias for the deployed model                                                                                                                                  |
| docker_registry_for_model_image          | `localhost:5000`                                 | #TODO update this - The Docker registry where images are stored                                                                                                   |
| mlflow_built_image_name                  | `bridgeai-mlops`                                 | The name of the MLFlow model Docker image                                                                                                                         |
| mlflow_built_image_tag                   | `latest`                                         | The tag for the MLFlow model Docker image                                                                                                                         |
| model_docker_build_context_pvc           | `model_docker_build_context_pvc`                 | Name of the PVC allocated for this DAG                                                                                                                            | 
| model_docker_push_secret                 | `ecr-credentials`                                | Name of the secret to authenticate ECR access                                                                                                                     |
| docker_build_pod_resource_limits_enabled | `True`                                           | Enables or disables resource constraints (CPU, memory, and ephemeral storage) for the Docker build pod. If `false`, no resource limits will be applied            |
| docker_build_pod_request_memory          | `4Gi`                                            | Minimum amount of memory requested for the Docker build pod to ensure resource allocation                                                                         |
| docker_build_pod_limit_memory            | `30Gi`                                           | Maximum memory limit allocated to the Docker build pod to prevent exceeding node capacity                                                                         |
| docker_build_pod_request_cpu             | `1`                                              | Minimum number of CPU cores requested for the Docker build pod to ensure sufficient processing power                                                              |
| docker_build_pod_limit_cpu               | `2`                                              | Maximum number of CPU cores allocated to the Docker build pod to cap CPU consumption                                                                              |
| docker_build_pod_request_eph_storage     | `8Gi`                                            | Minimum ephemeral storage requested for temporary storage during the Docker build process                                                                         |
| docker_build_pod_node_label_enabled      | `True`                                           | Enables or disables node label selection constraints for the Docker build pod. If `False`, no node label will be used                                             |
| docker_build_pod_node_label              | `["t3.large"]`                                   | The node label on which the Docker build pod should run. Airflow tasks will be scheduled on nodes of label specified in the list (like ["t3.large", "t3.medium"]) |


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

4. Open the Airflow web UI and trigger the DAG with name `create_model_image_to_deploy_dag_ecr`

---
## Notes:

### Creating docker registry secret
To create a docker registry secret named "docker-registry-secret" to set the variable `docker_reg_secret`

#TODO: add reference to the secret creation from `bridgeAI-gitops-infra` repo.
