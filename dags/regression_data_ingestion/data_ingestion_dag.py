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
data_url = "https://raw.githubusercontent.com/renjith-digicat/random_file_shares/main/HousingData.csv"  # Variable.get("data_path")
# mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
# docker_reg_secret = Variable.get("docker_reg_secret")
namespace = Variable.get("namespace")
base_image = "renjithdigicat/experiments:1.2"  # Variable.get("base_image")
config_map = Variable.get("config_map")
# connection_id = Variable.get("connection_id")
log_level = "INFO"  # Variable.get("log_level", default_var="INFO")
# in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
#     "true",
#     "1",
#     "t",
# )
# kubeconfig = (
#     Variable.get("kubeconfig", default_var="~/.kube/config")
#     if in_cluster
#     else None
# )
kubeconfig = "~/.kube/config"

# Define the volume and volume mount using k8s models
volume = k8s.V1Volume(
    name="data-ingestion-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name="data-ingestion-pvc"
    ),
)

volume_mount = k8s.V1VolumeMount(
    name="data-ingestion-volume",
    mount_path="/app/artefacts",
    sub_path=None,
    read_only=False,
)


@dag(schedule=None, catchup=False)
def data_ingestion_dag():
    """Regression data ingestion dag."""
    # Define KubernetesPodOperator to run the data ingestion container
    """
    # TODO: Split this large task into 3 separate tasks
    # preprocess >> train >> evaluate
    """
    data_collect_pod = KubernetesPodOperator(
        # kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_collection_task",
        name="regression-data-collect",
        cmds=["poetry", "run", "python", "src/data_gathering.py"],
        # image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "DATA_URL": data_url,
            "CONFIG_PATH": "./config.yaml",
            "LOG_LEVEL": log_level,
        },
        # volumes=[
        #     k8s.V1Volume(
        #         name="config-volume",
        #         config_map=k8s.V1ConfigMapVolumeSource(name=config_map),
        #     ),
        # ],
        # volume_mounts=[
        #     k8s.V1VolumeMount(
        #         name="config-volume",
        #         mount_path="/config",
        #         read_only=True,
        #     ),
        # ],
        volumes=[volume],
        volume_mounts=[volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        # in_cluster=in_cluster,
        in_cluster=False,
        config_file=kubeconfig,
    )

    data_clean_pod = KubernetesPodOperator(
        # kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_cleansing_task",
        name="regression-data-cleansing",
        cmds=["poetry", "run", "python", "src/data_cleansing.py"],
        # image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "CONFIG_PATH": "./config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[volume],
        volume_mounts=[volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        # in_cluster=in_cluster,
        in_cluster=False,
        config_file=kubeconfig,
    )

    data_split_pod = KubernetesPodOperator(
        # kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="data_split_task",
        name="regression-data-splitting",
        cmds=["poetry", "run", "python", "src/data_splitting.py"],
        # image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "CONFIG_PATH": "./config.yaml",
            "LOG_LEVEL": log_level,
        },
        volumes=[volume],
        volume_mounts=[volume_mount],
        is_delete_operator_pod=False,
        get_logs=True,
        # in_cluster=in_cluster,
        in_cluster=False,
        config_file=kubeconfig,
    )

    # TODO: create a task that can do this to automate the rest of the process
    # dvc_add_and_git_push_pod = None

    # Registering the task - Define the task dependencies here
    data_collect_pod >> data_clean_pod >> data_split_pod


# Instantiate the DAG
dag_instance = data_ingestion_dag()
