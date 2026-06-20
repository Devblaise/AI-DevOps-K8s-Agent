# Failure-scenario test harness

Ready-to-apply manifests that induce the four canonical Kubernetes failures the agent
is meant to diagnose, plus the expected diagnosis and fix for each. Use these to
validate Phase 5 end-to-end against a real cluster.

> **These fixtures are applied manually by you, never by the agent.** The
> investigation layer is strictly read-only — it never runs `apply`, `edit`,
> `delete`, `scale`, or `patch`. These manifests under `k8s-test/` are the only
> place in the repo allowed to create broken resources.

All fixtures live in the `k8s-agent-lab` namespace so you can scope an investigation
to them and tear everything down in one command.

## Prerequisites

- A local cluster (kind or minikube) reachable via `kubectl`.
- The backend running on the host: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- The frontend running: `cd frontend && npm run dev`

Create the namespace first:

```bash
kubectl apply -f k8s-test/00-namespace.yaml
```

To investigate from the dashboard: pick your cluster context, set the namespace to
`k8s-agent-lab`, and click **Investigate Cluster**. (Leaving the namespace blank scans
all namespaces, which also works but is noisier.)

---

## Scenario 1 — CrashLoopBackOff (missing env var)

```bash
kubectl apply -f k8s-test/crashloop.yaml
# wait ~30s for it to restart a few times
kubectl get pods -n k8s-agent-lab -l app=crashloop-app
```

- **What breaks:** the container requires `APP_DB_URL`, which is never set, so it
  exits 1 on every start and lands in `CrashLoopBackOff`.
- **Expected root cause:** the container is crash-looping because a required
  environment variable / config value (`APP_DB_URL`) is missing; the logs show the
  explicit `FATAL: APP_DB_URL must be set` message.
- **Expected fix:** provide `APP_DB_URL` (via `env`, a ConfigMap, or a Secret) so the
  container can start.

---

## Scenario 2 — ImagePullBackOff (bad image tag)

```bash
kubectl apply -f k8s-test/imagepull.yaml
kubectl get pods -n k8s-agent-lab -l app=imagepull-app
```

- **What breaks:** the image tag `nginx:this-tag-does-not-exist-9999` doesn't exist,
  so the kubelet can't pull it. The pod stays `Pending` with
  `ImagePullBackOff` / `ErrImagePull` and a `Warning Failed` event.
- **Expected root cause:** the referenced image tag cannot be pulled because it does
  not exist in the registry; the pod can't start.
- **Expected fix:** correct the image tag to one that exists (e.g. `nginx:1.27`).

---

## Scenario 3 — OOMKilled (memory limit too low)

```bash
kubectl apply -f k8s-test/oomkilled.yaml
# give it a few restarts
kubectl get pod -n k8s-agent-lab -l app=oomkilled-app \
  -o jsonpath='{.items[0].status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

- **What breaks:** the container allocates ~100MB but its memory limit is `16Mi`, so
  the kernel OOM-killer terminates it. The last terminated state reports
  `reason: OOMKilled`, and it crash-loops on restart.
- **Expected root cause:** the container is being OOMKilled because its memory limit
  (`16Mi`) is far below what it needs.
- **Expected fix:** raise the memory limit to match real usage (e.g. `128Mi`), or
  reduce the workload's memory footprint.

---

## Scenario 4 — Service selector mismatch

```bash
kubectl apply -f k8s-test/selector-mismatch.yaml
kubectl get endpoints web-svc -n k8s-agent-lab   # ENDPOINTS column will be <none>
```

- **What breaks:** the pods are healthy with label `app: web`, but the Service selects
  `app: wbe` (a typo). The Service matches zero pods and has no endpoints, so traffic
  to it goes nowhere even though the workload is fine.
- **Expected root cause:** the Service selector (`app=wbe`) doesn't match the pod
  labels (`app=web`), so the Service has no endpoints.
- **Expected fix:** correct the Service selector to `app: web`.

Note: the pod itself is healthy here, so this is the scenario that proves the agent
inspects **network/Service** evidence and not just pod status.

---

## Cluster picker check (multiple contexts)

The dashboard lists every context from your local kubeconfig and investigates the one
you select. To confirm it works with more than one context present:

```bash
kubectl config get-contexts -o name      # what the picker should show
```

Spin up a second local cluster if you only have one (e.g. `kind create cluster
--name agent-lab-2`), reload the dashboard, and confirm both contexts appear in the
picker and that investigating each one targets the right cluster.

---

## Reliability checks (friendly errors)

Each of these should show a friendly message in the UI — never a raw stack trace.

| Induce | How | Expected UI |
| --- | --- | --- |
| Cluster unreachable | Stop the cluster (`kind delete cluster` / `minikube stop`) then investigate | "Unable to reach the Kubernetes cluster. Check: kubeconfig path, cluster is running, kubectl permissions." |
| kubectl missing | Run the backend with `kubectl` off the PATH | "kubectl isn't installed or isn't on the PATH…" |
| Bad / missing kubeconfig | Point `KUBECONFIG` at a nonexistent file | "No usable kubeconfig was found…" |
| LLM failure | Unset `OPENROUTER_API_KEY` (or use a bad model id) and investigate a broken pod | Evidence still shows; the root-cause card reads "Diagnosis unavailable" with the reason |
| Healthy cluster | Investigate a namespace with no problems (e.g. `default` on a clean cluster) | "No issues found — cluster appears healthy" (a positive result, not an error) |
| Session expiry | Let the InsForge session expire / clear it | You're returned to the login screen rather than shown a data error |

---

## Cleanup

```bash
kubectl delete namespace k8s-agent-lab
```

This removes every fixture in one shot. (Delete the second kind cluster too if you
created one: `kind delete cluster --name agent-lab-2`.)
