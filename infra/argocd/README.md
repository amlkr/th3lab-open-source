# ArgoCD (Phase 2 GitOps)

Este directorio prepara la capa GitOps para llevar th3lab a cluster.

## Prerrequisitos

- Kubernetes operativo (k3s/k3d/eks/gke/aks)
- `kubectl`
- `argocd` CLI (opcional)

## Instalar ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

## Registrar app th3lab

Edita `apps/th3lab-phase2.yaml` con tu `repoURL` real y aplica:

```bash
kubectl apply -f infra/argocd/apps/th3lab-phase2.yaml
```

## Nota

La UI de th3lab no cambia en esta fase. Esta capa es solo despliegue/orquestación.

