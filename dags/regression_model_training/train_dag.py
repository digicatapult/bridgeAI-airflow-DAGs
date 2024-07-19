"""Model training Airflow DAG for Kubernetes."""

import os

from airflow.decorators import dag
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import models as k8s

# Env variables
"""
# TODO: probably change this when dvc data versioning is available-
# and pull the data directly from dvc remote without mounting the data path
"""
DATA_PATH = os.getenv("DATA_PATH")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
DOCKER_REG_SECRET = os.getenv("DOCKER_REG_SECRET")
NAMESPACE = os.getenv("NAMESPACE")
BASE_IMAGE = os.getenv("BASE_IMAGE")
CONFIG_MAP = os.getenv("CONFIG_MAP")
CONNECTION_ID = os.getenv("CONNECTION_ID")
IN_CLUSTER = os.getenv("IN_CLUSTER", "False").lower() in ("true", "1", "t")
KUBECONFIG = os.getenv("KUBECONFIG", "~/.kube/config") if IN_CLUSTER else None


@dag(schedule=None, catchup=False)
def model_training_dag():
    """Model training dag."""
    # Define KubernetesPodOperator to run the training container
    """
    # TODO: Split this large task into 3 separate tasks
    # preprocess >> train >> evaluate
    """
    training_pod = KubernetesPodOperator(
        kubernetes_conn_id=CONNECTION_ID,
        namespace=NAMESPACE,
        image=BASE_IMAGE,
        task_id="regression_model_training_task",
        name="regression-model-training",
        cmds=["poetry", "run", "python", "src/main.py"],
        image_pull_secrets=[k8s.V1LocalObjectReference(DOCKER_REG_SECRET)],
        env_vars={
            "DATA_PATH": DATA_PATH,
            "CONFIG_PATH": "/config/config.yaml",
            "MLFLOW_TRACKING_URI": MLFLOW_TRACKING_URI,
        },
        volumes=[
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=CONFIG_MAP),
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
        in_cluster=IN_CLUSTER,
        config_file=KUBECONFIG,
    )

    # Registering the task - Define the task dependencies here
    training_pod


# Instantiate the DAG
dag_instance = model_training_dag()
