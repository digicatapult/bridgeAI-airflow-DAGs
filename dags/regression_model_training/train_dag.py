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
data_path = Variable.get("data_path")
mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
docker_reg_secret = Variable.get("docker_reg_secret")
namespace = Variable.get("namespace")
base_image = Variable.get("base_image")
config_map = Variable.get("config_map")
connection_id = Variable.get("connection_id")
log_level = Variable.get("log_level", default_var="INFO")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)
# kubeconfig = (
#     Variable.get("kubeconfig", default_var="~/.kube/config")
#     if in_cluster
#     else None
# )


@dag(schedule=None, catchup=False)
def model_training_dag():
    """Model training dag."""
    # Define KubernetesPodOperator to run the training container
    """
    # TODO: Split this large task into 3 separate tasks
    # preprocess >> train >> evaluate
    """
    training_pod = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="regression_model_training_task",
        name="regression-model-training",
        cmds=["poetry", "run", "python", "src/main.py"],
        image_pull_secrets=[k8s.V1LocalObjectReference(docker_reg_secret)],
        env_vars={
            "DATA_PATH": data_path,
            "CONFIG_PATH": "/config/config.yaml",
            "MLFLOW_TRACKING_URI": mlflow_tracking_uri,
            "LOG_LEVEL": log_level,
        },
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
        # config_file=kubeconfig,
    )

    # Registering the task - Define the task dependencies here
    training_pod


# Instantiate the DAG
dag_instance = model_training_dag()
