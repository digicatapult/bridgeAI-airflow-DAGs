"""Model training Airflow DAG for Kubernetes."""

from airflow.decorators import dag
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import \
    KubernetesPodOperator
from kubernetes.client import models as k8s

# Env variables
data_url = "https://raw.githubusercontent.com/renjith-digicat/random_file_shares/main/HousingData.csv"  # Variable.get("data_path")
docker_reg_secret = Variable.get("docker_reg_secret")
namespace = Variable.get("namespace")
base_image = "renjithdigicat/experiments:1.14"  # Variable.get("base_image_data_ingestion")

config_map = Variable.get("data_ingestion_configmap")
connection_id = Variable.get("connection_id")
log_level = "INFO"  # Variable.get("log_level", default_var="INFO")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)

# kubeconfig = "~/.kube/config"

# Define the volume and volume mount using k8s models
pvc_volume = k8s.V1Volume(
    name="data-ingestion-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name="data-ingestion-pvc"
    ),
)

pvc_volume_mount = k8s.V1VolumeMount(
    name="data-ingestion-volume",
    mount_path="/app/artefacts",
    sub_path=None,
    read_only=False,
)

# Same path referencing as a different one from within the repo
# TODO: confirm if this is the right way
pvc_volume_mount_from_repo = k8s.V1VolumeMount(
    name="data-ingestion-volume",
    mount_path="/app/local_repo/artefacts",
    sub_path=None,
    read_only=False,
)

config_volumes = k8s.V1Volume(
        name="config-volume",
        config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
    )
config_volume_mounts = k8s.V1VolumeMount(
        name="config-volume",
        mount_path="/config",
        read_only=True,
    )


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
        # image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "DATA_URL": data_url,
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volumes],
        volume_mounts=[pvc_volume_mount, config_volume_mounts],
        is_delete_operator_pod=False,
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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volumes],
        volume_mounts=[pvc_volume_mount, config_volume_mounts],
        is_delete_operator_pod=False,
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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volumes],
        volume_mounts=[pvc_volume_mount, config_volume_mounts],
        is_delete_operator_pod=False,
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
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "CONFIG_PATH": "/config/config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[pvc_volume, config_volumes],
        volume_mounts=[pvc_volume_mount_from_repo, config_volume_mounts],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
    )

    # Registering the task - Define the task dependencies here
    data_collect_pod >> data_clean_pod >> data_split_pod >> data_push_pod


# Instantiate the DAG
dag_instance = data_ingestion_dag()
