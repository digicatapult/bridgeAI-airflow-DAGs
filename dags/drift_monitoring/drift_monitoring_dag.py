"""Drift monitoring Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s

# Airflow variables
namespace = Variable.get("namespace")
base_image = Variable.get("base_image_drift_monitoring")
config_map = Variable.get("drift_monitoring_configmap")
connection_id = Variable.get("connection_id")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)
dvc_remote = Variable.get("dvc_remote")
dvc_endpoint_url = Variable.get("dvc_endpoint_url")
dvc_remote_region = Variable.get("dvc_remote_region", default_var="eu-west-2")

# Retrieve AWS connection details - this must be set already
conn_id = Variable.get("aws_conn_name", default_var="aws_default")
conn = BaseHook.get_connection(conn_id)

# Extract connection details
dvc_access_key_id = conn.login  # Access Key ID
dvc_secret_access_key = conn.password  # Secret Access Key

github_secret = Variable.get("github_secret", default_var="github-auth")
github_secret_username_key = Variable.get(
    "github_secret_username_key", default_var="username"
)
github_secret_password_key = Variable.get(
    "github_secret_password_key", default_var="password"
)
log_level = Variable.get("log_level", default_var="INFO")

data_repo = Variable.get("data_repo")
historical_data_version = Variable.get("historical_data_version")
new_data_version = Variable.get("new_data_version")
drift_report_bucket = Variable.get("drift_report_bucket")
model_endpoint = Variable.get("model_endpoint")
pvc_claim_name = Variable.get(
    "drift_monitoring_pvc", default_var="drift-monitoring-pvc"
)

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

# Define PVC
pvc_volume = k8s.V1Volume(
    name="drift-monitoring-pvc",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name=pvc_claim_name
    ),
)

# Mount PVC
pvc_volume_mount = k8s.V1VolumeMount(
    name="drift-monitoring-pvc",
    mount_path="/app/artefacts",
    sub_path=None,
    read_only=False,
)

config_volume = k8s.V1Volume(
    name="config-volume",
    config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
)
config_volume_mount = k8s.V1VolumeMount(
    name="config-volume",
    mount_path="/config",
    read_only=True,
)

env_vars = [
    k8s.V1EnvVar(name="CONFIG_PATH", value="/config/config.yaml"),
    k8s.V1EnvVar(name="LOG_LEVEL", value=log_level),
    k8s.V1EnvVar(name="DVC_REMOTE", value=dvc_remote),
    k8s.V1EnvVar(name="DVC_ENDPOINT_URL", value=dvc_endpoint_url),
    k8s.V1EnvVar(name="DVC_ACCESS_KEY_ID", value=dvc_access_key_id),
    k8s.V1EnvVar(name="DVC_SECRET_ACCESS_KEY", value=dvc_secret_access_key),
    k8s.V1EnvVar(name="AWS_DEFAULT_REGION", value=dvc_remote_region),
    k8s.V1EnvVar(name="DATA_REPO", value=data_repo),
    k8s.V1EnvVar(
        name="HISTORICAL_DATA_VERSION", value=historical_data_version
    ),
    k8s.V1EnvVar(name="NEW_DATA_VERSION", value=new_data_version),
    k8s.V1EnvVar(name="DRIFT_REPORT_BUCKET", value=drift_report_bucket),
    k8s.V1EnvVar(name="MODEL_ENDPOINT", value=model_endpoint),
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
    k8s.V1EnvVar(name="CONFIG_PATH", value="/config/config.yaml"),
]


@dag(schedule=None, catchup=False)
def drift_monitoring_dag():
    """Drift monitoring dag."""
    # Define KubernetesPodOperator to fetch the data from dvc
    fetch_data = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="fetch_data_from_dvc",
        name="fetch-data-from-dvc",
        cmds=["poetry", "run", "python", "src/get_data.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        service_account_name="airflow",
    )

    generate_drift_report = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="generate_drift_report",
        name="generate-drift-report",
        cmds=["poetry", "run", "python", "src/drift_report.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        service_account_name="airflow",
    )

    push_drift_report = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="push_drift_report",
        name="push-drift-report",
        cmds=["poetry", "run", "python", "src/upload_report.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        service_account_name="airflow",
    )

    fetch_data >> generate_drift_report >> push_drift_report


# Instantiate the DAG
dag_instance = drift_monitoring_dag()
