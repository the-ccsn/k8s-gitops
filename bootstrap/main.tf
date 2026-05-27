provider "helm" {
  kubernetes = {
    config_path = var.kubeconfig
  }
}

provider "kubernetes" {
  config_path = var.kubeconfig
}

module "flux_operator_bootstrap" {
  source  = "controlplaneio-fluxcd/flux-operator-bootstrap/kubernetes"
  version = "0.7.0"

  revision = var.bootstrap_revision

  job = {
    tolerations = [
      {
        key      = "node.kubernetes.io/not-ready"
        operator = "Exists"
        effect   = "NoSchedule"
      }
    ]
    host_network = true

    env = {  
      KUBERNETES_SERVICE_HOST = "127.0.0.1"
      KUBERNETES_SERVICE_PORT = "6443"
    }  
  }

  gitops_resources = {
    instance_yaml = file("${path.root}/../clusters/${var.cluster_name}/flux.yaml")
    prerequisites = {  
      charts = [{  
        name        = "cilium"  
        repository  = "quay.io/cilium/charts/cilium"  
        namespace   = "kube-system"  
        version     = "1.19.4"  
        values_yaml = file("${path.root}/../infra/pre-controllers/overlays/${var.cluster_name}/cilium/values.yaml")  
      }]  
    }
  }

  managed_resources = {
    secrets_yaml = <<-YAML
apiVersion: v1
kind: Secret
metadata:
  name: sops-age
  namespace: flux-system
stringData:
  age.agekey: '${replace(var.sops_age_key, "'", "''")}'
    YAML
    runtime_info = {
      labels = {
        "reconcile.fluxcd.io/watch" = "Enabled"
      }
      data = {
        cluster_name   = var.cluster_name
        cluster_region = "eu-west-2"
      }
    }
  }
}
