# bridgeAI-airflow-DAGs

## Testing the DAGs on local KIND cluster

1. Delete the kind-cluster `bridgeai-gitops-infra` if it already exists
```shell
kind delete cluster --name bridgeai-gitops-infra
```
2. Clone the bridgeAI infra repo, [`bridgeai-gitops-infra`](https://github.com/digicatapult/bridgeAI-gitops-infra)
```shell
git clone https://github.com/digicatapult/bridgeAI-gitops-infra.git
```
3. Modify `bridgeai-gitops-infra` repo - `flux/clusters/kind-cluster/config/airflow-values.yaml` with the branch of this DAGs repo that you want to test; for example `branch: feature/data-ingestion`
4. Modify `bridgeai-gitops-infra` repo - `flux/clusters/kind-cluster/base/flux-system/gotk-sync.yaml` with branch of the infra repo that you are using to test; for example `test/data-ingestion`
5. Add the changes in above files to the branch `test/data-ingestion`
6. Commit and push the change to `bridgeai-gitops-infra` `test/data-ingestion` branch
7. Update the `feature/data-ingestion` branch of [`bridgeAI-airflow-DAGs`](https://github.com/digicatapult/bridgeAI-airflow-DAGs) repo with the new dag and relevant changes that you want to test
8. From the `bridgeai-gitops-infra` repo, `test/data_ingestion` branch, run the following to bring up a local kind cluster. Check the [readme](https://github.com/digicatapult/bridgeAI-gitops-infra/tree/main/flux) for more details.
```shell
./flux/scripts/add-kind-cluster.sh
```
9. From the `bridgeai-gitops-infra` repo, `test/data_ingestion` branch, run the following to install and start the infra on the above created cluster. Check the [readme](https://github.com/digicatapult/bridgeAI-gitops-infra/tree/main/flux) for more details.
```shell
lux/scripts/install-flux.sh -b test/data_ingestion
```
You can check the logs by running `kubectl events --watch` from a terminal
10. Inspect the configmaps if needed
```shell
kubectl get configmaps
kubectl describe configmap <config-map-name>
```
11. Ensure you have the PVCs needed up and ready
```shell
kubectl get pvc
```
12. Access the Airflow UI - http://localhost:3080/airflow
13. You can update the airflow variable from the airflow UI; Admin -> Variables
14. Open the DAG and trigger it. You can inspect the logs in the airflow UI as well as kubectl events.