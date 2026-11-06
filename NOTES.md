# LAB 7

## install

- docker desktop
- helm 3
- kubectl

## rustfs

- clone kubernetes-tutorial
- update `rustfs-config.yaml`
    - change `access_key` and `secret_key`
    - change `storageclass` `name` to `hostpath` to match docker for local dev (changed from `standard` for GKE)
- update `deploy-local-dev.sh`
    - add `kubectl port-forward --namespace rustfs-ns svc/rustfs-svc 9000:9000 9001:9001 &` from tutorial
    - comment all lines with `minio`
- from `06-rustfs` after config changes
    - `./install-rustfs.sh`

## create buckets

`./deploy-local-dev.sh` after above changes made for rustfs.

Login with creds in `06-rustfs/rustfs-config.yaml`. Create `output` and `queue` bucket.

## rest-server.py

build out `rest/rest-server.py` according to `rest/README.md`. Comments within.

## worker-server.py

build out `worker/worker-server.py` according to `worker/README.md`. Comments also within.

## testing

to test locally, i just stood the python services up on local host with the k8s pods running in local docker. i was able to access the site at localhost:5000 and test that everything works.

## cleanups

stop port-forwards
- `pkill -f "kubectl port-forward"`

ingress, app pods, secrets 

- `kubectl delete ingress rest-ingress --ignore-not-found`
- `kubectl delete -f rest/rest-deployment.yaml -f rest/rest-service.yaml --ignore-not-found`
- `kubectl delete -f worker/worker-deployment.yaml --ignore-not-found`
- `kubectl delete -f logs/logs-deployment.yaml --ignore-not-found`
- `kubectl delete -f redis/redis-deployment.yaml -f redis/redis-service.yaml --ignore-not-found`
- `kubectl delete secret rustfs-creds --ignore-not-found`

RustFS and its data

- `helm uninstall rustfs -n rustfs-ns`
- `kubectl delete namespace rustfs-ns`

optional: the nginx ingress controller itself

- `kubectl delete namespace ingress-nginx`

## setups 

rustfs install:
- `cd kubernetes-tutorial/06-rustfs && ./install-rustfs.sh && cd ../..`

secret setup (this password means nothing to me)
- `kubectl create secret generic rustfs-creds --from-literal=RUSTFS_USER=gejo6742 --from-literal=RUSTFS_PASS=SuperBatteryCat`

ingress controller from tutorial
- `kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.13.3/deploy/static/provider/cloud/deploy.yaml`

else
`./deploy-local-dev.sh`
`kubectl apply -f rest/rest-ingress.yaml`


## checkers 

- `kubectl get pods,pvc -n rustfs-ns` # rustfs status
- `kubectl get pods -n ingress-nginx` # nginx controller status
- `kubectl get pods` # general status