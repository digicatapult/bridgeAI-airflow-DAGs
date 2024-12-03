"""Regression model data ingestion Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s

# Get Airflow Variables
data_url = Variable.get("data_url")
namespace = Variable.get("namespace")
base_image = Variable.get("base_image_data_ingestion")
dvc_remote = Variable.get("dvc_remote")
dvc_endpoint_url = Variable.get("dvc_endpoint_url")

# Retrieve AWS connection details - this must be set already
conn_id = Variable.get("aws_conn_name", default_var="aws_default")
conn = BaseHook.get_connection(conn_id)

# Extract connection details
dvc_access_key_id = conn.login  # Access Key ID
dvc_secret_access_key = conn.password  # Secret Access Key

config_map = Variable.get("data_ingestion_configmap")
connection_id = Variable.get("connection_id")
log_level = Variable.get("log_level", default_var="INFO")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)
github_secret = Variable.get("github_secret", default_var="github-auth")
github_secret_username_key = Variable.get(
    "github_secret_username_key", default_var="username"
)
github_secret_password_key = Variable.get(
    "github_secret_password_key", default_var="password"
)
pvc_claim_name = Variable.get(
    "data_ingestion_pvc", default_var="data-ingestion-pvc"
)

# Define PVC
pvc_volume = k8s.V1Volume(
    name="data-ingestion-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name=pvc_claim_name
    ),
)

# Mount PVC
pvc_volume_mount = k8s.V1VolumeMount(
    name="data-ingestion-volume",
    mount_path="/app/artefacts",
    sub_path=None,
    read_only=False,
)

# Mount PVC from a different location for another pod
pvc_volume_mount_from_repo = k8s.V1VolumeMount(
    name="data-ingestion-volume",
    mount_path="/app/local_repo/artefacts",
    sub_path=None,
    read_only=False,
)

# Define config volume
config_volume = k8s.V1Volume(
    name="config-volume",
    config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
)
# Mount config volume
config_volume_mount = k8s.V1VolumeMount(
    name="config-volume",
    mount_path="/config",
    read_only=True,
)

# Define the github secret as environment variables
secret = k8s.V1SecretEnvSource(name="github-auth")

base_image_needs_auth = Variable.get(
    "is_base_image_authenticated", default_var="False"
).lower() in (
    "true",
    "1",
    "t",
)
if base_image_needs_auth:
    docker_reg_secret = Variable.get("docker_reg_secret")
    image_pull_secrets = [k8s.V1LocalObjectReference(docker_reg_secret)]
else:
    image_pull_secrets = None

# Define the environment variables
env_vars = [
    k8s.V1EnvVar(name="CONFIG_PATH", value="/config/config.yaml"),
    k8s.V1EnvVar(name="LOG_LEVEL", value=log_level),
    k8s.V1EnvVar(name="DVC_REMOTE", value=dvc_remote),
    k8s.V1EnvVar(name="DVC_ENDPOINT_URL", value=dvc_endpoint_url),
    k8s.V1EnvVar(name="DVC_ACCESS_KEY_ID", value=dvc_access_key_id),
    k8s.V1EnvVar(name="DVC_SECRET_ACCESS_KEY", value=dvc_secret_access_key),
    k8s.V1EnvVar(name="AWS_ACCESS_KEY_ID", value=dvc_access_key_id),
    k8s.V1EnvVar(name="AWS_SECRET_ACCESS_KEY", value=dvc_secret_access_key),
    k8s.V1EnvVar(
        name="GITHUB_USERNAME",
        value_from=k8s.V1EnvVarSource(
            secret_key_ref=k8s.V1SecretKeySelector(
                name=github_secret, key=github_secret_username_key
            )
        ),
    ),
    k8s.V1EnvVar(
        name="GITHUB_PASSWORD",
        value_from=k8s.V1EnvVarSource(
            secret_key_ref=k8s.V1SecretKeySelector(
                name=github_secret, key=github_secret_password_key
            )
        ),
    ),
]


@dag(schedule=None, catchup=False)
def data_ingestion_dag():
    """Regression data ingestion dag."""
    data_collect_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_collection_task",
        name="regression-data-collect",
        cmds=["poetry", "run", "python", "src/data_gathering.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars={
            "DATA_URL": data_url,
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
    )

    data_clean_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_cleansing_task",
        name="regression-data-cleanse",
        cmds=["poetry", "run", "python", "src/data_cleansing.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars={
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
    )

    data_split_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_split_task",
        name="regression-data-split",
        cmds=["poetry", "run", "python", "src/data_splitting.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars={
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
    )

    data_push_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_push_task",
        name="regression-data-push",
        cmds=["poetry", "run", "python", "src/data_push.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount_from_repo, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
    )

    # Registering the task - task dependencies
    data_collect_pod >> data_clean_pod >> data_split_pod >> data_push_pod


# Instantiate the DAG
dag_instance = data_ingestion_dag()
