"""Model training Airflow DAG for Kubernetes.

To create a docker registry secret `DOCKER_REG_SECRET`;
`
kubectl create secret docker-registry docker-registry-secret \
  --docker-username=<docker-username> \
  --docker-password=<docker-password> \
  --docker-email=<docker-email> \
  --docker-server=<docker-server> \
  --namespace=bridgeai
`
To create a configmap `CONFIG_MAP`,
1. `kubectl create configmap training-config \
        --from-file=config.yaml --namespace=bridgeai`
    The current config.yaml file is directly taken form the
    `bridgeAI-regression-model-training` repo
to verify the config,
2. `kubectl describe configmap training-config --namespace=bridgeai`


If using a KIND cluster, to mount a host path to the model training container;
1. Mount the host local path to the kind cluster
    a) Create a kind-config.yaml file with the following content
        ```
        kind: Cluster
        apiVersion: kind.x-k8s.io/v1alpha4
        nodes:
          - role: control-plane
            extraMounts:
              - hostPath: /host/local/directory/tobe/mounted
                containerPath: /mnt/data  # path name for the cluster
        ```
    b) Create a kind cluster with the created config
        `kind create cluster --name bridgeai --config kind-config.yaml`
2. Mount the cluster mount point path to the container
    a) create volume
        ```
        volumes=[
            k8s.V1Volume(
                name="host-data-volume",
                host_path=k8s.V1HostPathVolumeSource(
                    path="/mnt/data",
                    type="Directory"
                )
            ]
        ```
    b)  use the volume mount
        ```
        volume_mounts=[
            k8s.V1VolumeMount(
                name="host-data-volume",
                mount_path="/app/artefacts",
                read_only=False,
                )
            ]
        ```
"""

import os

from airflow.decorators import dag
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
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
KUBECONFIG = os.getenv("KUBECONFIG", "~/.kube/config")


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
        in_cluster=False,  # If Airflow is running in cluster - set to True
        config_file=KUBECONFIG,
    )

    # Registering the task - Define the task dependencies here
    training_pod


# Instantiate the DAG
dag_instance = model_training_dag()
