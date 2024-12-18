"""Docker image generation for model deployment DAG."""

from airflow.decorators import dag
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from kubernetes.client import (
    V1Affinity,
    V1NodeAffinity,
    V1NodeSelector,
    V1NodeSelectorRequirement,
    V1NodeSelectorTerm,
)
from kubernetes.client import models as k8s

# Env variables
namespace = Variable.get("namespace")
connection_id = Variable.get("connection_id")
base_image = Variable.get("base_image_model_image_generation")
in_cluster = Variable.get("in_cluster", default_var="False").lower() in (
    "true",
    "1",
    "t",
)

mlflow_tracking_uri = Variable.get("mlflow_tracking_uri")
mlflow_tracking_username = Variable.get("mlflow_tracking_username")
mlflow_tracking_password = Variable.get("mlflow_tracking_password")
deploy_model_name = Variable.get("deploy_model_name")
deploy_model_alias = Variable.get("deploy_model_alias")
docker_registry = Variable.get("docker_registry_for_model_image")
mlflow_built_image_name = Variable.get("mlflow_built_image_name")
mlflow_built_image_tag = Variable.get("mlflow_built_image_tag")
pvc_claim_name = Variable.get(
    "model_docker_build_context_pvc",
    default_var="model-docker-build-context-pvc",
)
docker_push_secret_name = Variable.get(
    "docker_push_secret_name",
    default_var="ecr-credentials",
)

enable_resource_constraints = Variable.get(
    "docker_build_pod_resource_limits_enabled", default_var="True"
).lower() in (
    "true",
    "1",
    "t",
)

enable_node_selection = Variable.get(
    "docker_build_pod_node_label_enabled", default_var="True"
).lower() in (
    "true",
    "1",
    "t",
)

if enable_resource_constraints:
    # Retrieve Airflow variables for resources
    request_memory = Variable.get(
        "docker_build_pod_request_memory", default_var="4Gi"
    )
    request_cpu = Variable.get("docker_build_pod_request_cpu", default_var="1")
    request_eph_storage = Variable.get(
        "docker_build_pod_request_eph_storage", default_var="8Gi"
    )
    limit_memory = Variable.get(
        "docker_build_pod_limit_memory", default_var="30Gi"
    )
    limit_cpu = Variable.get("docker_build_pod_limit_cpu", default_var="2")

    resources = k8s.V1ResourceRequirements(
        requests={
            "memory": request_memory,
            "cpu": request_cpu,
            "ephemeral-storage": request_eph_storage,
        },
        limits={
            "memory": limit_memory,
            "cpu": limit_cpu,
        },
    )
else:
    resources = None

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

env_vars = [
    k8s.V1EnvVar(name="MLFLOW_TRACKING_URI", value=mlflow_tracking_uri),
    k8s.V1EnvVar(
        name="MLFLOW_TRACKING_USERNAME", value=mlflow_tracking_username
    ),
    k8s.V1EnvVar(
        name="MLFLOW_TRACKING_PASSWORD", value=mlflow_tracking_password
    ),
    k8s.V1EnvVar(name="DEPLOY_MODEL_NAME", value=deploy_model_name),
    k8s.V1EnvVar(name="DEPLOY_MODEL_ALIAS", value=deploy_model_alias),
    k8s.V1EnvVar(name="DOCKER_REGISTRY", value=docker_registry),
    k8s.V1EnvVar(
        name="MLFLOW_BUILT_IMAGE_NAME", value=mlflow_built_image_name
    ),
    k8s.V1EnvVar(name="MLFLOW_BUILT_IMAGE_TAG", value=mlflow_built_image_tag),
]

# Define PVC
pvc_volume = k8s.V1Volume(
    name="docker-context-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name=pvc_claim_name,
    ),
)

# Mount PVC
pvc_volume_mount = k8s.V1VolumeMount(
    name="docker-context-volume",
    mount_path="/app/mlflow-dockerfile",
)

# Secret for container registry authentication
secret_volume = k8s.V1Volume(
    name="docker-push-secret-volume",
    secret=k8s.V1SecretVolumeSource(
        secret_name=docker_push_secret_name,
        items=[k8s.V1KeyToPath(key=".dockerconfigjson", path="config.json")],
    ),
)
secret_volume_mount = k8s.V1VolumeMount(
    name="docker-push-secret-volume", mount_path="/kaniko/.docker/"
)

if enable_node_selection:
    node_label = Variable.get("docker_build_pod_node_label", "t3.2xlarge")
    # Define node affinity
    node_affinity = V1Affinity(
        node_affinity=V1NodeAffinity(
            required_during_scheduling_ignored_during_execution=V1NodeSelector(
                node_selector_terms=[
                    V1NodeSelectorTerm(
                        match_expressions=[
                            V1NodeSelectorRequirement(
                                key="node.kubernetes.io/instance-type",
                                operator="In",
                                values=[node_label],
                            )
                        ]
                    )
                ]
            )
        )
    )
else:
    node_affinity = None


@dag(schedule=None, catchup=False)
def create_model_image_to_deploy_dag():
    """Model deployment dag."""
    # KubernetesPodOperator to generate Dockerfile
    generate_dockerfile = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        image=base_image,
        task_id="generate_dockerfile",
        name="generate-dockerfile",
        cmds=["poetry", "run", "python", "src/main.py"],
        image_pull_secrets=image_pull_secrets,
        env_vars=env_vars,
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        volume_mounts=[pvc_volume_mount],
        volumes=[pvc_volume],
        service_account_name="airflow",
    )

    # Build and push image
    build_and_push = KubernetesPodOperator(
        kubernetes_conn_id=connection_id,
        namespace=namespace,
        task_id="build_and_push_docker_image",
        name="build-and-push-docker-image",
        image="bitnami/kaniko:latest",
        cmds=["/kaniko/executor"],
        arguments=[
            "--dockerfile=/app/mlflow-dockerfile/Dockerfile",
            "--context=dir:///app/mlflow-dockerfile",
            f"--destination={docker_registry}/"
            f"{mlflow_built_image_name}:{mlflow_built_image_tag}",
        ],
        is_delete_operator_pod=False,
        get_logs=True,
        in_cluster=in_cluster,
        image_pull_secrets=image_pull_secrets,
        volume_mounts=[pvc_volume_mount, secret_volume_mount],
        volumes=[pvc_volume, secret_volume],
        # Set resource constraints
        container_resources=resources,
        affinity=node_affinity,
        service_account_name="airflow",
    )

    # Registering the task - Define the task dependencies here
    generate_dockerfile >> build_and_push


# Instantiate the DAG
dag_instance = create_model_image_to_deploy_dag()
