"""Model training Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s

# Env variables
mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
mlflow_tracking_username = Variable.get("mlflow_tracking_username")
mlflow_tracking_password = Variable.get("mlflow_tracking_password")
namespace = Variable.get("namespace")
base_image = Variable.get("base_image_model_training")
dvc_remote = Variable.get("dvc_remote")

# Retrieve AWS connection details - this must be set already
conn_id = Variable.get("aws_conn_name", default_var="aws_default")
conn = BaseHook.get_connection(conn_id)

# Extract connection details
dvc_access_key_id = conn.login  # Access Key ID
dvc_secret_access_key = conn.password  # Secret Access Key

dvc_endpoint_url = Variable.get("dvc_endpoint_url")
dvc_remote_region = Variable.get("dvc_remote_region", default_var="eu-west-2")
data_version = Variable.get("data_version")
config_map = Variable.get("model_training_configmap")
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
    "model_training_pvc", default_var="model-training-pvc"
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

deploy_as_code = Variable.get("deploy_as_code", default_var="False")
deploy_model_name = Variable.get("deploy_model_name")
deploy_model_alias = Variable.get("deploy_model_alias")

# Define PVC
pvc_volume = k8s.V1Volume(
    name="model-training-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name=pvc_claim_name
    ),
)

# Mount PVC
pvc_volume_mount = k8s.V1VolumeMount(
    name="model-training-volume",
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
    k8s.V1EnvVar(name="DATA_VERSION", value=data_version),
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
    k8s.V1EnvVar(name="MLFLOW_TRACKING_URI", value=mlflow_tracking_uri),
    k8s.V1EnvVar(
        name="MLFLOW_TRACKING_USERNAME", value=mlflow_tracking_username
    ),
    k8s.V1EnvVar(
        name="MLFLOW_TRACKING_PASSWORD", value=mlflow_tracking_password
    ),
    k8s.V1EnvVar(name="DEPLOY_AS_CODE", value=deploy_as_code),
    k8s.V1EnvVar(name="DEPLOY_MODEL_NAME", value=deploy_model_name),
    k8s.V1EnvVar(name="DEPLOY_MODEL_ALIAS", value=deploy_model_alias),
]


def extract_run_id(**kwargs):
    ti = kwargs["ti"]
    run_id = ti.xcom_pull(task_ids="model_training", key="return_value")[
        "run_id"
    ]
    if run_id is None:
        raise ValueError("No run_id found in XCom for task 'model_training'")
    return run_id


@dag(schedule=None, catchup=False)
def model_training_dag():
    """Model training dag."""
    # Define KubernetesPodOperator to fetch the data from dvc
    data_fetch_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_fetch_from_dvc",
        name="data-fetch-from-dvc",
        cmds=["poetry", "run", "python", "src/fetch_data.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
    )

    preprocess_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="preprocess_data",
        name="preprocess-data",
        cmds=["poetry", "run", "python", "src/preprocess.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
    )

    model_train_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="model_training",
        name="model-training",
        cmds=["poetry", "run", "python", "src/train.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        do_xcom_push=True,
    )

    extract_run_id_task = PythonOperator(
        task_id="extract_run_id",
        python_callable=extract_run_id,
        provide_context=True,
    )

    evaluation_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="model_evaluation",
        name="model-evaluation",
        cmds=[
            "poetry",
            "run",
            "python",
            "src/evaluate.py",
            "--run_id",
            "{{ ti.xcom_pull(task_ids='extract_run_id') }}",
        ],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        volumes=[pvc_volume, config_volume],
        volume_mounts=[pvc_volume_mount, config_volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
    )

    # Registering the task - Define the task dependencies here
    (
        data_fetch_pod
        >> preprocess_pod
        >> model_train_pod
        >> extract_run_id_task
        >> evaluation_pod
    )


# Instantiate the DAG
dag_instance = model_training_dag()
