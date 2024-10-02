"""Model deployment Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s

# Env variables
docker_reg_secret = Variable.get("docker_reg_secret")
namespace = Variable.get("namespace")
connection_id = Variable.get("connection_id")
base_image = Variable.get("model_image_generation_base_image")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)

mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
deploy_model_name = Variable.get("deploy_model_name")
deploy_model_alias = Variable.get("deploy_model_alias")
docker_registry = Variable.get("docker_registry")
mlflow_built_image_name = Variable.get("mlflow_built_image_name")
mlflow_built_image_tag = Variable.get("mlflow_built_image_tag")


env_vars = [
    k8s.V1EnvVar(name="MLFLOW_TRACKING_URI", value=mlflow_tracking_uri),
    k8s.V1EnvVar(name="DEPLOY_MODEL_NAME", value=deploy_model_name),
    k8s.V1EnvVar(name="DEPLOY_MODEL_ALIAS", value=deploy_model_alias),
    k8s.V1EnvVar(name="DOCKER_REGISTRY", value=docker_registry),
    k8s.V1EnvVar(
        name="MLFLOW_BUILT_IMAGE_NAME", value=mlflow_built_image_name
    ),
    k8s.V1EnvVar(name="MLFLOW_BUILT_IMAGE_TAG", value=mlflow_built_image_tag),
]


@dag(schedule=None, catchup=False)
def create_model_image_to_deploy_dag():
    """Model deployment dag."""
    # Define KubernetesPodOperator to fetch the data from dvc
    deploy_model = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="create_model_image_to_deploy",
        name="create-model-image-to-deploy",
        # cmds=["poetry", "run", "python", "src/main.py"],
        cmds=["/bin/sh", "-c"],
        arguments=["sleep 3600"],
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars=env_vars,
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
        security_context={
            "privileged": True,
            "capabilities": {"add": ["SYS_ADMIN"]},
        },
        container_security_context={
            "privileged": True,
            "capabilities": {"add": ["SYS_ADMIN"]},
        },
    )

    # Registering the task - Define the task dependencies here
    deploy_model


# Instantiate the DAG
dag_instance = create_model_image_to_deploy_dag()
