"""Model training Airflow DAG for Kubernetes."""

import os

from airflow.decorators import dag
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import \
    KubernetesPodOperator
from kubernetes.client import models as k8s

# Env variables
# TODO: remove the defaults
DATA_PATH = os.getenv("DATA_PATH", "/app/artefacts/HousingData.csv")
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI", "http://host.docker.internal:5000"
)
DOCKER_REG_SECRET = os.getenv("DOCKER_REG_SECRET", "docker-registry-secret")
NAMESPACE = os.getenv("NAMESPACE", "bridgeai")
BASE_IMAGE = os.getenv("BASE_IMAGE", "renjithdigicat/bridgeai-regression:0.1")
CONFIG_MAP = os.getenv("CONFIG_MAP", "training-config")
# KUBECONFIG = os.getenv("KUBECONFIG", "~/.kube/config")


@dag(schedule=None, catchup=False)
def model_training_dag():
    """Model training dag."""
    # Define KubernetesPodOperator to run the training container
    training_pod = KubernetesPodOperator(
        task_id="regression_model_training_task",
        name="regression-model-training",
        namespace=NAMESPACE,
        image=BASE_IMAGE,
        cmds=["poetry", "run", "python", "src/main.py"],
        image_pull_secrets=[k8s.V1LocalObjectReference(DOCKER_REG_SECRET)],
        env_vars={
            "DATA_PATH": DATA_PATH,
            "CONFIG_PATH": "/config/config.yaml",
            "MLFLOW_TRACKING_URI": MLFLOW_TRACKING_URI,
        },
        volumes=[
            # TODO: remove this temporary host data path mount
            k8s.V1Volume(
                name="host-data-volume",
                host_path=k8s.V1HostPathVolumeSource(
                    path="/mnt/data", type="Directory"
                ),
            ),
            k8s.V1Volume(
                name="config-volume",
                config_map=k8s.V1ConfigMapVolumeSource(name=CONFIG_MAP),
            ),
        ],
        volume_mounts=[
            # TODO: remove this temporary data path mount
            k8s.V1VolumeMount(
                name="host-data-volume",
                mount_path="/app/artefacts",
                read_only=False,
            ),
            k8s.V1VolumeMount(
                name="config-volume",
                mount_path="/config",
                read_only=True,
            ),
        ],
        is_delete_operator_pod=True,
        get_logs=True,
        in_cluster=True,  # If Airflow is running in cluster - set to True
        config_file=KUBECONFIG,
    )

    # Registering the task - Define the task dependencies here
    training_pod


# Instantiate the DAG
dag_instance = model_training_dag()
