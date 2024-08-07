"""Model training Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import \
    KubernetesPodOperator
from kubernetes.client import models as k8s

# Env variables
"""
# TODO: probably change the use of `data_path` when dvc data versioning is
available and pull the data directly from dvc remote.
"""
mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
docker_reg_secret = Variable.get("docker_reg_secret")
namespace = Variable.get("namespace")
base_image = Variable.get("base_image_model_training")
dvc_remote = Variable.get("dvc_remote")
dvc_access_key_id = Variable.get("dvc_access_key_id")
dvc_secret_access_key = Variable.get("dvc_secret_access_key")
data_version = "data-v1.0.0"  # Variable.get("data_version")
config_map = Variable.get("model_training_configmap")
connection_id = Variable.get("connection_id")
log_level = Variable.get("log_level", default_var="INFO")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",)
github_secret = Variable.get("github_secret", default_var="github-auth")
github_secret_username_key = Variable.get(
    "github_secret_username_key", default_var="username"
)
github_secret_password_key = Variable.get(
    "github_secret_password_key", default_var="password"
)


env_vars = [
    k8s.V1EnvVar(name="CONFIG_PATH", value="/config/config.yaml"),
    k8s.V1EnvVar(name="LOG_LEVEL", value=log_level),
    k8s.V1EnvVar(name="DVC_REMOTE", value=dvc_remote),
    k8s.V1EnvVar(name="DVC_ACCESS_KEY_ID", value=dvc_access_key_id),
    k8s.V1EnvVar(name="DVC_SECRET_ACCESS_KEY", value=dvc_secret_access_key),
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
]


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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars=env_vars,
        volumes=[
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
            ),
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name="config-volume",
                mount_path="/config",
                read_only=True,
            ),
        ],
        is_delete_operator_pod=True,
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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars=env_vars,
        volumes=[
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
            ),
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name="config-volume",
                mount_path="/config",
                read_only=True,
            ),
        ],
        is_delete_operator_pod=True,
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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars=env_vars,
        volumes=[
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
            ),
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name="config-volume",
                mount_path="/config",
                read_only=True,
            ),
        ],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
    )

    evaluation_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="model_evaluation",
        name="model-evaluation",
        cmds=["poetry", "run", "python", "src/train.py"],
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars=env_vars,
        volumes=[
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
            ),
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name="config-volume",
                mount_path="/config",
                read_only=True,
            ),
        ],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=in_cluster,
    )

    # Registering the task - Define the task dependencies here
    data_fetch_pod >> preprocess_pod >> model_train_pod >> evaluation_pod


# Instantiate the DAG
dag_instance = model_training_dag()
