[
  {
    imageName = "adyanth/cloudflare-operator";
    imageDigest = "sha256:6b168dc237d50e3d36cc5df86bf2be7981700a49d7a4ae02548f4762ec0d7aaa";
    finalImageName = "docker.io/adyanth/cloudflare-operator";
    finalImageTag = "0.13.1";
    archiveHash = "sha256-UFLHLGTyi5CBy8SCcQyvLAJlPIiMLQKKog0DDIhKfno=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cloudflare-operator-system"; name = "cloudflare-operator-controller-manager"; }
    ];
  }
  {
    imageName = "bitnami/kubectl";
    imageDigest = "sha256:172d4889e49c3b66d91a3a5afc289448fa1407dda782b9817ccfd8d1b064660b";
    finalImageName = "docker.io/bitnami/kubectl";
    finalImageTag = "latest";
    archiveHash = "sha256-AEMiiNRZkpIOvlfm7ASmrulBS8XLylFaZ1ABqXDhN7Y=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "unknown ns"; name = "logto"; }
    ];
  }
  {
    imageName = "busybox";
    imageDigest = "sha256:fd8d9aa63ba2f0982b5304e1ee8d3b90a210bc1ffb5314d980eb6962f1a9715d";
    finalImageName = "docker.io/library/busybox";
    finalImageTag = "latest";
    archiveHash = "sha256-6QfG5F03Lx3394n+pKmScYo3EF/JI+f/zQ2RFd5CxQI=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Job"; namespace = "unknown ns"; name = "logto-pre-app-1"; }
    ];
  }
  {
    imageName = "cloudflare/cloudflared";
    imageDigest = "sha256:59bab8d3aceec09bf6bdb07d6beca0225ca5cd7ab79436a87ea97978fe1dc4f9";
    finalImageName = "docker.io/cloudflare/cloudflared";
    finalImageTag = "2026.5.0";
    archiveHash = "sha256-IVT8IUv20gFrdIeBLJop6qszY7vaXN5diNR1RJ7Xnds=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cloudflare-operator-system"; name = "default-tunnel-v6"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-core";
    imageDigest = "sha256:887a85b8ea98b76bfc9f715f1a0785bb99f9a1034241513902dd6e95be922a83";
    finalImageName = "docker.io/goharbor/harbor-core";
    finalImageTag = "v2.15.1";
    archiveHash = "sha256-i5Pz+Wo1eSSb7xxI0qWLvt9nY3x9DQ42BR2DaHj3t+g=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-core"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-jobservice";
    imageDigest = "sha256:0de4fd2ce3a02d3e6591b439e4674ea085885ddf43652b44004cc67eb19dba12";
    finalImageName = "docker.io/goharbor/harbor-jobservice";
    finalImageTag = "v2.15.1";
    archiveHash = "sha256-IOMWTPioMzuWYY7mOpQIWE1sDjJLplN6K4XPJl/JYBM=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-jobservice"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-portal";
    imageDigest = "sha256:ac55161c57a8351807adf8f8def264bdd52667c371d0436beefebdac4341c9e2";
    finalImageName = "docker.io/goharbor/harbor-portal";
    finalImageTag = "v2.15.1";
    archiveHash = "sha256-6giFWh8hvKI8dv2kQFhPfgA1e3IwNmy7tqnuy8R48VQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-portal"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-registryctl";
    imageDigest = "sha256:554147a956989175f63f8d41573d716c6ddf6052acd1749c88c0f99ce6ee2bff";
    finalImageName = "docker.io/goharbor/harbor-registryctl";
    finalImageTag = "v2.15.1";
    archiveHash = "sha256-0nar7lmPwn7aKXnL0vMbFHQGFERs6aYqfZgMRujw9Os=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-registry"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/registry-photon";
    imageDigest = "sha256:ebf0325c2661729dbb317cbf839608eb8b15cfa158911a94976f2c21563c466e";
    finalImageName = "docker.io/goharbor/registry-photon";
    finalImageTag = "v2.15.1";
    archiveHash = "sha256-VRXhI0dtdtmQgK1+gLLkY32dvoJLLZKVm93AhzgxuiQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-registry"; }
    ];
  }
  {
    imageName = "docker.io/library/busybox";
    imageDigest = "sha256:9532d8c39891ca2ecde4d30d7710e01fb739c87a8b9299685c63704296b16028";
    finalImageName = "docker.io/library/busybox";
    finalImageTag = "1.37";
    archiveHash = "sha256-UaNeBTNG0HRJl+LJlmhCFBA+7qnvy7wuXm8ZIM4tmEQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "vaultwarden"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "vaultwarden"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "unknown ns"; name = "vaultwarden-vaultwarden"; }
    ];
  }
  {
    imageName = "docker.io/library/python";
    imageDigest = "sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a";
    finalImageName = "docker.io/library/python";
    finalImageTag = "3.14-alpine";
    archiveHash = "sha256-oXI5nXZgQsPL29gXKudeiMC1LBelnSdIiXRxzW2F2T4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "egress-system"; name = "proxy-engine"; }
    ];
  }
  {
    imageName = "docker.io/longhornio/longhorn-manager";
    imageDigest = "sha256:0f80ca11ac4eb7522f4e6e801a7afc9909ea8d3041575f3d029964c46590f096";
    finalImageName = "docker.io/longhornio/longhorn-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-91T1bF2mfPbVh+s62HTiFI5o7VKraze51HoXcdjBQv8=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "longhorn-system"; name = "longhorn-manager"; }
      { kind = "Deployment"; namespace = "longhorn-system"; name = "longhorn-driver-deployer"; }
      { kind = "Job"; namespace = "longhorn-system"; name = "longhorn-post-upgrade"; }
      { kind = "Job"; namespace = "longhorn-system"; name = "longhorn-pre-upgrade"; }
      { kind = "Job"; namespace = "longhorn-system"; name = "longhorn-uninstall"; }
    ];
  }
  {
    imageName = "docker.io/longhornio/longhorn-share-manager";
    imageDigest = "sha256:c11559e998ea982e6bac1637d66cc2aaab662a6b546709f2e54e2bfa50ffb0c3";
    finalImageName = "docker.io/longhornio/longhorn-share-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-aI3HfqoRbpqIxa+0O5KkzJx3aHrr8iyhFiy4EJPBksE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "longhorn-system"; name = "longhorn-manager"; }
    ];
  }
  {
    imageName = "docker.io/longhornio/longhorn-ui";
    imageDigest = "sha256:885bc78f99f31da0d9b0fd8f533a53558a3aa81f9719c62e0d3c69ed8456d5b7";
    finalImageName = "docker.io/longhornio/longhorn-ui";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-xboFUEX0vuI6Z+pNQqLfg8X0EbB0lZoswRoC/ReTVq4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "longhorn-system"; name = "longhorn-ui"; }
    ];
  }
  {
    imageName = "docker.io/rancher/local-path-provisioner";
    imageDigest = "sha256:1eba82e9c386038b4af6d69cca7519fac738c28c42735ed48ce70c882ad0d80f";
    finalImageName = "docker.io/rancher/local-path-provisioner";
    finalImageTag = "v0.0.36";
    archiveHash = "sha256-7elybhSANToIiMssIKIFXidv1OlZ8o971VDwfNdKe9E=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "local-path-provisioner"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "local-path-provisioner"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kube-system"; name = "local-path-provisioner"; }
    ];
  }
  {
    imageName = "docker.io/squat/generic-device-plugin";
    imageDigest = "sha256:66c8d5c270eb2b721f1064c549b9b7898152a6d2f0163380a5d37dc7636c20ff";
    finalImageName = "docker.io/squat/generic-device-plugin";
    finalImageTag = "0.2.0";
    archiveHash = "sha256-Rx3V2OK8e5AoF8M/cRo01YiuyVvIPD5oqpRAUezDhN0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "kube-system"; name = "generic-device-plugin"; }
    ];
  }
  {
    imageName = "docker.io/vaultwarden/server";
    imageDigest = "sha256:d626d04934cd1192ad8ced1adb975099fca78cec33ab467d2d3c923cde7f3b0c";
    finalImageName = "docker.io/vaultwarden/server";
    finalImageTag = "1.36.0";
    archiveHash = "sha256-0nfPTInWIYZGyPwRRC1aYKAKC7jVQeRlIWe3HmyNzrE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "vaultwarden"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "vaultwarden"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "unknown ns"; name = "vaultwarden-vaultwarden"; }
    ];
  }
  {
    imageName = "ghcr.io/cloudnative-pg/cloudnative-pg";
    imageDigest = "sha256:0dfff19ba7b52ca25851a1010028b6940fff2e233290465af1cfb08a5f3f4661";
    finalImageName = "ghcr.io/cloudnative-pg/cloudnative-pg";
    finalImageTag = "1.29.1";
    archiveHash = "sha256-xU71L4zdgfcXbZodsYIrYFnoMJxvCWaiZ1gdkEhocS4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cnpg-system"; name = "cnpg"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cnpg-system"; name = "cnpg"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cnpg-system"; name = "cnpg-cloudnative-pg"; }
    ];
  }
  {
    imageName = "ghcr.io/cloudnative-pg/plugin-barman-cloud";
    imageDigest = "sha256:0b9c428123313d93efbec26bdef85e91f2130a7bd8e382a767de12b3938f6271";
    finalImageName = "ghcr.io/cloudnative-pg/plugin-barman-cloud";
    finalImageTag = "v0.12.0";
    archiveHash = "sha256-W0glk+3dwzIHLJZ9XsIKXr494zBa6O+xZykwLLTKeug=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cnpg-system"; name = "cnpg-plugin-barman-cloud"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cnpg-system"; name = "cnpg-plugin-barman-cloud"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cnpg-system"; name = "cnpg-plugin-barman-cloud"; }
    ];
  }
  {
    imageName = "ghcr.io/controlplaneio-fluxcd/flux-operator";
    imageDigest = "sha256:d7423e1d6b0e206cc5b9758fa8615d7694664ed906c5087f4202eeb14187421a";
    finalImageName = "ghcr.io/controlplaneio-fluxcd/flux-operator";
    finalImageTag = "v0.50.0";
    archiveHash = "sha256-WUndNOtEwGizy/ix1TK2YrJXfGWaOT6eqsDopVyW0u8=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "flux-system"; name = "flux-operator"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "flux-system"; name = "flux-operator"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "flux-system"; name = "flux-operator"; }
    ];
  }
  {
    imageName = "ghcr.io/flux-iac/tofu-controller";
    imageDigest = "sha256:e16d8295e66f73d66f6904a9129d8aedfa84612d1e8b5a8e122fda99d28af09c";
    finalImageName = "ghcr.io/flux-iac/tofu-controller";
    finalImageTag = "v0.16.3";
    archiveHash = "sha256-gx5PoE785o3xUbtH1CekZj/BO2Vkxm8iqBv7ftGM1vQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "flux-system"; name = "tofu-controller"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "flux-system"; name = "tofu-controller"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "flux-system"; name = "tofu-controller"; }
    ];
  }
  {
    imageName = "ghcr.io/grafana/grafana-operator";
    imageDigest = "sha256:3abeaccdf54e9e02c2f4b6215be594c8f78b94a866961ada7f92b677bf33c9b4";
    finalImageName = "ghcr.io/grafana/grafana-operator";
    finalImageTag = "v5.23.0";
    archiveHash = "sha256-lJeZ0Xv3Sg3UUWJsniCgpU1r+kPmMmsf5dzpNdjiuMM=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "grafana-operator"; name = "grafana-operator"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "grafana-operator"; name = "grafana-operator"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-monitoring"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "grafana-operator"; name = "grafana-operator"; }
    ];
  }
  {
    imageName = "ghcr.io/headlamp-k8s/headlamp-plugin-cert-manager";
    imageDigest = "sha256:d7d0321a90c0347e2e4f9f7e362ecaa10a36592cc5ac8fd1514df11c476b43fe";
    finalImageName = "ghcr.io/headlamp-k8s/headlamp-plugin-cert-manager";
    finalImageTag = "v0.1.0";
    archiveHash = "sha256-K8fgubGpDrmeagg3nqTUnP9PN0SW77TLN2CcRTyc+m8=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "ghcr.io/headlamp-k8s/headlamp-plugin-flux";
    imageDigest = "sha256:055377b9011dcc73235e8969c488ecd92af5cb70aa5d5df0f66c1cea667fdccb";
    finalImageName = "ghcr.io/headlamp-k8s/headlamp-plugin-flux";
    finalImageTag = "v0.6.0";
    archiveHash = "sha256-4ADArqRNWx9gzmhBa9rpEYTJZJ14rY6N78bAi6wqZ8Y=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "ghcr.io/headlamp-k8s/headlamp";
    imageDigest = "sha256:c9754bae1d799220da0547e51ceee234f6e66ebadc138518ca73e33ecd331e59";
    finalImageName = "ghcr.io/headlamp-k8s/headlamp";
    finalImageTag = "v0.42.0";
    archiveHash = "sha256-NX0uuwxxZMwBHuJCWDhVvxgV8CO69j5y6ODttDP0vPg=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "prod"; name = "headlamp"; }
    ];
  }
  {
    imageName = "ghcr.io/isning/redroid-operator";
    imageDigest = "sha256:f5e367011b405a3b5c594a6821d8806b4990d09cdc91eae9e4983a106dc9142e";
    finalImageName = "ghcr.io/isning/redroid-operator";
    finalImageTag = "0.1.7";
    archiveHash = "sha256-lQ/CZ7qBZ2hj8TQ7IwFrENloIcZ+9nFNlZJqCca4nZ0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "redroid-operator"; name = "redroid-operator"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "redroid-operator"; name = "redroid-operator"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "redroid-operator"; name = "redroid-operator"; }
    ];
  }
  {
    imageName = "ghcr.io/kube-vip/kube-vip";
    imageDigest = "sha256:840305b94ef2a89abb3b7fd2b09edfbde690d90052020da4dff90679fe892da2";
    finalImageName = "ghcr.io/kube-vip/kube-vip";
    finalImageTag = "v1.1.2";
    archiveHash = "sha256-qnsQ6zq4wrll/Jj3hpQFOv7D1s0vVN0LJcZYUGJAIew=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "kube-system"; name = "kube-vip-ds"; }
    ];
  }
  {
    imageName = "ghcr.io/logto-io/logto";
    imageDigest = "sha256:dabb2b3d087bb40fed8f33508ca16432ddf5c03f3e0846e36fe1f399a00ab1f3";
    finalImageName = "ghcr.io/logto-io/logto";
    finalImageTag = "1.40.1";
    archiveHash = "sha256-oFd5jZ9dNxupuqXmC0z1VXVFgr3bY5x4h1SgrNOQ3qI=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "unknown ns"; name = "logto"; }
      { kind = "Job"; namespace = "unknown ns"; name = "logto-pre-app-1"; }
    ];
  }
  {
    imageName = "ghcr.io/naval-group/headlamp-kubevirt";
    imageDigest = "sha256:7cdff58fdda4f3ad7b7a208b83744ec82648795056cf726f0ce5df2501ee3d14";
    finalImageName = "ghcr.io/naval-group/headlamp-kubevirt";
    finalImageTag = "0.2.2";
    archiveHash = "sha256-kF1hnipCHJmyujf3G8o1q/LtogrPKMDMW5jD1976rKk=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "headlamp"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "ghcr.io/sagernet/sing-box";
    imageDigest = "sha256:da0e2331395c9025a85fa58892772b4cdbe5f2e530e93defeec3968175d06c6d";
    finalImageName = "ghcr.io/sagernet/sing-box";
    finalImageTag = "v1.13.12";
    archiveHash = "sha256-ADuYPHGPIlR6Krx0VT0TYSsuicKWKYDIv14IWvixPYk=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "egress-system"; name = "proxy-engine"; }
    ];
  }
  {
    imageName = "ghcr.io/the-ccsn/k8s-gitops/tf-runner";
    imageDigest = "sha256:8600a5292bb1773b55486e093289258f2dc3f16112856a11f8a523f018472d28";
    finalImageName = "ghcr.io/the-ccsn/k8s-gitops/tf-runner";
    finalImageTag = "v0.16.3-custom-202605251544";
    archiveHash = "sha256-MLvkJawyPgAhCWkeu7wA+EL5BrUb3CTt6lV4UDuys+w=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "flux-system"; name = "tofu-controller"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/backing-image-manager";
    imageDigest = "sha256:fc7b656501e59896326de6d228319d883ae55591c1a2c90292043eab66c33e7b";
    finalImageName = "docker.io/longhornio/backing-image-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-ecKBIWRd9e25WBpRpsOqpocqXWoyhCfZNwIBJq3anvo=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/csi-attacher";
    imageDigest = "sha256:fe417c28a6b86f8e7e5d49fc223e22e9ab457f894d2c4a321932d136dc2c2530";
    finalImageName = "docker.io/longhornio/csi-attacher";
    finalImageTag = "v4.11.0-20260428";
    archiveHash = "sha256-oN/9s+EEruDQzisLOAxbOg5x5Ix5zC5EmvPNV5KD484=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/csi-node-driver-registrar";
    imageDigest = "sha256:e82a8c8f800d7fbb3c1edf3f90b557768091821a44d52280093394f7918ccb68";
    finalImageName = "docker.io/longhornio/csi-node-driver-registrar";
    finalImageTag = "v2.16.0-20260428";
    archiveHash = "sha256-Z5K2gzKEtYcSR39rNzb+GuAlZ2q1umY+jN/hl6nChj4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/csi-provisioner";
    imageDigest = "sha256:9e519a21a77c060104716e1f98222bb46ab617778a3bfcd861c87119a8256764";
    finalImageName = "docker.io/longhornio/csi-provisioner";
    finalImageTag = "v5.3.0-20260428";
    archiveHash = "sha256-ZWkVkZFGslWvLBNSg9sKMydin28CewVXH7KvF3F1qmw=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/csi-resizer";
    imageDigest = "sha256:41cb674d1154e798aa2c20f53f72ee2a5597f1369bcad5878d1708aee47f6663";
    finalImageName = "docker.io/longhornio/csi-resizer";
    finalImageTag = "v2.1.0-20260428";
    archiveHash = "sha256-x4tmWHuO4q9MRomDBR9nLsWsr0U1jrFFHC/Un+OeheA=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/csi-snapshotter";
    imageDigest = "sha256:1975fac3890f4e08b98792881cb597502112ce0eeeaaef383e52458c96db94c5";
    finalImageName = "docker.io/longhornio/csi-snapshotter";
    finalImageTag = "v8.5.0-20260428";
    archiveHash = "sha256-LFVR0dmW/5CvheVeVWNIjHoWYFR+9XmIYTgSWCxdQXE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/livenessprobe";
    imageDigest = "sha256:eae162f7e70fb981f90d9206f299dddaf590c0c896cfb67acceca12cef526a44";
    finalImageName = "docker.io/longhornio/livenessprobe";
    finalImageTag = "v2.18.0-20260428";
    archiveHash = "sha256-eTQFv1UehSQohij3wSAhnxXuBGAVAjtl3dsVkQQioxY=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-cli";
    imageDigest = "sha256:c2e57e131cc001418f8ad329eb8d25f9fb69fa0eb0e546e1b6ee94aa22916381";
    finalImageName = "docker.io/longhornio/longhorn-cli";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-TLjDx0rsjuZyuE1zwJQYcOCpuIDae/N/Z4wOEQdCxgQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-engine";
    imageDigest = "sha256:7482e0437fbf475e1e32696fab22f47bf99b1ef8d067ffce9e34028347722628";
    finalImageName = "docker.io/longhornio/longhorn-engine";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-ALMQer+0umoi3n5KgvtRWvXsgvO/I8poJAGglf5onJg=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-instance-manager";
    imageDigest = "sha256:16dac125ef30bd3a375bc8ff7d10636ea0302d22d208c0cfb1be37ebb93ca30b";
    finalImageName = "docker.io/longhornio/longhorn-instance-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-xBLes/g67kW0fpCKheoo5BkGbdeCglalXh/99AZPlng=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-manager";
    imageDigest = "sha256:0f80ca11ac4eb7522f4e6e801a7afc9909ea8d3041575f3d029964c46590f096";
    finalImageName = "docker.io/longhornio/longhorn-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-91T1bF2mfPbVh+s62HTiFI5o7VKraze51HoXcdjBQv8=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-share-manager";
    imageDigest = "sha256:c11559e998ea982e6bac1637d66cc2aaab662a6b546709f2e54e2bfa50ffb0c3";
    finalImageName = "docker.io/longhornio/longhorn-share-manager";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-aI3HfqoRbpqIxa+0O5KkzJx3aHrr8iyhFiy4EJPBksE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/longhorn-ui";
    imageDigest = "sha256:885bc78f99f31da0d9b0fd8f533a53558a3aa81f9719c62e0d3c69ed8456d5b7";
    finalImageName = "docker.io/longhornio/longhorn-ui";
    finalImageTag = "v1.11.2";
    archiveHash = "sha256-xboFUEX0vuI6Z+pNQqLfg8X0EbB0lZoswRoC/ReTVq4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "longhornio/support-bundle-kit";
    imageDigest = "sha256:cf2a89ed18a73e32b3fe657aefb8f819a1c6734df888821b3dff056b360fe222";
    finalImageName = "docker.io/longhornio/support-bundle-kit";
    finalImageTag = "v0.0.84";
    archiveHash = "sha256-Tsj80hXjlW6jWw3kYx21ZwoL0F+OuzY8PlXb6qKmnnM=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "longhorn-system"; name = "longhorn"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "mendhak/http-https-echo";
    imageDigest = "sha256:d072446da821a767d05dc19fa5ab6a27b1150bfb5c6ecfaecf3a2e5f9812794c";
    finalImageName = "docker.io/mendhak/http-https-echo";
    finalImageTag = "40";
    archiveHash = "sha256-CgGyghmEZGpr4kDXsIdxcSCi73/dQxPRX88gg8aN8Io=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "staging"; name = "echo"; }
    ];
  }
  {
    imageName = "nginx";
    imageDigest = "sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de";
    finalImageName = "docker.io/library/nginx";
    finalImageTag = "mainline-alpine";
    archiveHash = "sha256-IuU35fXh3ReyujqgasRzaL2WnSifc0kOQWBXNGSMv60=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "i319-reroute"; name = "i319-reroute-proxy"; }
    ];
  }
  {
    imageName = "postgres";
    imageDigest = "sha256:df7bca0066e6f60cc3dd32faa70caddec20e2c22b58932f79498e5704b23854a";
    finalImageName = "docker.io/library/postgres";
    finalImageTag = "15-alpine";
    archiveHash = "sha256-l6C/PkHvMOxA1omKfh6i4Le/7Wbcdx4xqLxBAU/6gUE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "Job"; namespace = "unknown ns"; name = "logto-pre-app-1"; }
    ];
  }
  {
    imageName = "quay.io/cilium/cilium";
    imageDigest = "sha256:2eb67991eaa9368ba199c2fac2c573cb0ffdeb79184533344f42fc9a7ff6af3c";
    finalImageName = "quay.io/cilium/cilium";
    finalImageTag = "v1.19.4";
    archiveHash = "sha256-ryD/JBP9kzMo9MwtOynQBLsslXq+2aE4JvIZgZEztJY=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "kube-system"; name = "cilium"; }
    ];
  }
  {
    imageName = "quay.io/cilium/hubble-relay";
    imageDigest = "sha256:59af8c0d561e560c2a042e7600a3496bc0367df8fbf868aa68d5834c8ec1a431";
    finalImageName = "quay.io/cilium/hubble-relay";
    finalImageTag = "v1.19.4";
    archiveHash = "sha256-A2JpV1AWc7sJFOReySU8+q0YKR7gZ3kBG5H+oeCQrFk=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kube-system"; name = "hubble-relay"; }
    ];
  }
  {
    imageName = "quay.io/cilium/hubble-ui-backend";
    imageDigest = "sha256:fac0c300ae119274edca11fd89b1ad23c788792d8bc4ea2ba631c709e8d3c688";
    finalImageName = "quay.io/cilium/hubble-ui-backend";
    finalImageTag = "v0.13.5";
    archiveHash = "sha256-kxiZjZ0IRaHo6dD/KG0QVcQYMFPdSELhUnB3Z5z12V0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kube-system"; name = "hubble-ui"; }
    ];
  }
  {
    imageName = "quay.io/cilium/hubble-ui";
    imageDigest = "sha256:f7d514fc54d784ed6df9d58cf0e97648b143f92b766dd1780ed3fc845bd4c516";
    finalImageName = "quay.io/cilium/hubble-ui";
    finalImageTag = "v0.13.5";
    archiveHash = "sha256-YL/QAcolkztR+e12y6NDv4c7ybuFDnnR6vqf4mmdEIg=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kube-system"; name = "hubble-ui"; }
    ];
  }
  {
    imageName = "quay.io/cilium/operator-generic";
    imageDigest = "sha256:1aa2b62735e7d8ab49ee840ae59c346932024c88901579121395c1271b435f71";
    finalImageName = "quay.io/cilium/operator-generic";
    finalImageTag = "v1.19.4";
    archiveHash = "sha256-v8gGpP3VvpRtqqlz1f6YKRI0yMPdTXxwIRYzOAwkjWA=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kube-system"; name = "cilium"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-pre-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kube-system"; name = "cilium-operator"; }
    ];
  }
  {
    imageName = "quay.io/jetstack/cert-manager-cainjector";
    imageDigest = "sha256:6f5a644135887b2aa7d5cc145072fa56421560e3586ff1f184358022d490f4e1";
    finalImageName = "quay.io/jetstack/cert-manager-cainjector";
    finalImageTag = "v1.20.2";
    archiveHash = "sha256-tIBS8mb8WmVFgHvY5JK9Jr5uHSYJXv6+7XR37sKEkrE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cert-manager"; name = "cert-manager-cainjector"; }
    ];
  }
  {
    imageName = "quay.io/jetstack/cert-manager-controller";
    imageDigest = "sha256:fe0623d7d04a382c888f03343a3a2da716e0d96ad3d5d790c0ebcbcb2a4329a5";
    finalImageName = "quay.io/jetstack/cert-manager-controller";
    finalImageTag = "v1.20.2";
    archiveHash = "sha256-gyNKBHUd4jXiApWt9lGDPoYk1bEd3U7mTgEXeHe9lE0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cert-manager"; name = "cert-manager"; }
    ];
  }
  {
    imageName = "quay.io/jetstack/cert-manager-startupapicheck";
    imageDigest = "sha256:4e2a69b4a0cc9627905bbeecf720f95d5153ca39cacdab923d2748e73556792b";
    finalImageName = "quay.io/jetstack/cert-manager-startupapicheck";
    finalImageTag = "v1.20.2";
    archiveHash = "sha256-+DOo9Rd8WTG/FwVH/siYGJG3KeaW5NmsPv0lqchli8Y=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Job"; namespace = "cert-manager"; name = "cert-manager-startupapicheck"; }
    ];
  }
  {
    imageName = "quay.io/jetstack/cert-manager-webhook";
    imageDigest = "sha256:baf651128b9f05c426cbd5e60e2036bf382c99ca270f49d0757d6f7d2452f4e5";
    finalImageName = "quay.io/jetstack/cert-manager-webhook";
    finalImageTag = "v1.20.2";
    archiveHash = "sha256-S8jLxPAgf6Vy3EXfp3FtPG8JjG54d7POKK/No75QIvM=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "cert-manager"; name = "cert-manager"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cert-manager"; name = "cert-manager-webhook"; }
    ];
  }
  {
    imageName = "quay.io/kiali/kiali-operator";
    imageDigest = "sha256:b0a733933bbcc7f4d36ab4aaf3134a51ff67d2215bdae4cecc0786840a6ad6f0";
    finalImageName = "quay.io/kiali/kiali-operator";
    finalImageTag = "v2.24.0";
    archiveHash = "sha256-1Y4lKoJ1aO4xnXG20P/sE7aTvgZlhv4JRRpHYPjieRM=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "kiali-operator"; name = "kiali"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "kiali-operator"; name = "kiali"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kiali-operator"; name = "kiali-kiali-operator"; }
    ];
  }
  {
    imageName = "quay.io/kubevirt/cdi-operator";
    imageDigest = "sha256:42ce149c020523b466cd8cb5e413bad9800d93f502d82ced69a2d98a01944ce5";
    finalImageName = "quay.io/kubevirt/cdi-operator";
    finalImageTag = "v1.65.0";
    archiveHash = "sha256-UssLI3sDgHU2ZMrBuP6Qwd+/YBo3M0XdrR1BvtIUZFQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cdi"; name = "cdi-operator"; }
    ];
  }
  {
    imageName = "quay.io/kubevirt/cluster-network-addons-operator";
    imageDigest = "sha256:6d19b3d8a7b406fc4106f2b1ddbb5894884fba4fb854558e39d14e54e644f818";
    finalImageName = "quay.io/kubevirt/cluster-network-addons-operator";
    finalImageTag = "v0.102.0";
    archiveHash = "sha256-24svgvKbf6e7+0mChjclgg5RSuIBbUzxsAiK4pU/vGc=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cluster-network-addons"; name = "cluster-network-addons-operator"; }
    ];
  }
  {
    imageName = "quay.io/kubevirt/virt-operator";
    imageDigest = "sha256:a6cd48ee32c53fc09944cb1b3b709b8ef634f0168472b2409d1a31d0c345cbcb";
    finalImageName = "quay.io/kubevirt/virt-operator";
    finalImageTag = "v1.8.1";
    archiveHash = "sha256-shEKhLfCGxc+pY+2bhN0zEPX9SQlw29zj8KqzRqXWjk=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kubevirt"; name = "virt-operator"; }
    ];
  }
  {
    imageName = "rancher/kubectl";
    imageDigest = "sha256:05d2b313e2f397e0ade252136aed47abd72d56ead11d1b027ac70f66362c8495";
    finalImageName = "docker.io/rancher/kubectl";
    finalImageTag = "v1.36.0";
    archiveHash = "sha256-YpOd+xnsiOtSjzvNPDQEfQ0G6Vq1scg4udg3rQaTc0o=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-general"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "CronJob"; namespace = "egress-system"; name = "proxy-engine-daily-restarter"; }
    ];
  }
  {
    imageName = "registry-1.docker.io/bitnami/redis-exporter";
    imageDigest = "sha256:27abbdd44585399a5b34f3dc329235381c5e1091b264e886757812d99d5666e3";
    finalImageName = "registry-1.docker.io/bitnami/redis-exporter";
    finalImageTag = "latest";
    archiveHash = "sha256-9rs3hmKNKXgP3t+5X3fzsFBWzjrQsH1PPoj/tCWOl1I=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
      { kind = "HelmRelease"; namespace = "prod"; name = "logto-redis"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "StatefulSet"; namespace = "harbor"; name = "harbor-redis-master"; }
      { kind = "StatefulSet"; namespace = "prod"; name = "logto-redis-master"; }
    ];
  }
  {
    imageName = "registry-1.docker.io/bitnami/redis";
    imageDigest = "sha256:1d391b67aeec1254d333aa2640bca526e7d7026e93b2035ccfbc62f7a7a8c248";
    finalImageName = "registry-1.docker.io/bitnami/redis";
    finalImageTag = "latest";
    archiveHash = "sha256-NQjvvMwkfflIICFFmuN48KMhT0Q+JXlugUN/JSUDYLU=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
      { kind = "HelmRelease"; namespace = "prod"; name = "logto-redis"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-configs"; }
      ]
      [
        { kind = "HelmRelease"; namespace = "prod"; name = "logto-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "apps"; }
      ]
    ];
    targets = [
      { kind = "StatefulSet"; namespace = "harbor"; name = "harbor-redis-master"; }
      { kind = "StatefulSet"; namespace = "prod"; name = "logto-redis-master"; }
    ];
  }
  {
    imageName = "registry.istio.io/release/install-cni";
    imageDigest = "sha256:c37347421fe4d99b34d193b79437e7186fda762b2ae8231f28e2b9add287b9b5";
    finalImageName = "registry.istio.io/release/install-cni";
    finalImageTag = "1.30.0-rc.0-distroless";
    archiveHash = "sha256-YHw4kFUcra/OgFPZCl0b4AYK9P9+P4yk8VQ+XI04uPY=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "istio-system"; name = "istio-cni"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "istio-system"; name = "istio-cni"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "istio-system"; name = "istio-cni-node"; }
    ];
  }
  {
    imageName = "registry.istio.io/release/pilot";
    imageDigest = "sha256:db64101f2e1828323950dc1bf12ed35bcf77121fc3cbb505bef31a5fb7dfe605";
    finalImageName = "registry.istio.io/release/pilot";
    finalImageTag = "1.30.0-rc.0-distroless";
    archiveHash = "sha256-jkLTtqhOt8OcIbqJeFk/Ogdx7PtnVWPd6G9fky3TUm8=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "istio-system"; name = "istiod"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "istio-system"; name = "istiod"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "istio-system"; name = "istiod"; }
    ];
  }
  {
    imageName = "registry.istio.io/release/proxyv2";
    imageDigest = "sha256:9ac03a22e3cbc83def63242c4609ddf5b3a7bdac9fa06fa815eb72611fd44616";
    finalImageName = "registry.istio.io/release/proxyv2";
    finalImageTag = "1.30.0-rc.0-distroless";
    archiveHash = "sha256-E0fv5Z0dL5eLpG9o57/36U30T2s0B7FqzSbiU0Hr0zQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "istio-system"; name = "istio-base"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [];
  }
  {
    imageName = "registry.istio.io/release/ztunnel";
    imageDigest = "sha256:d2e1bdab8c85c335c173828a3fd34898a46fbb9139b409f646b4e8e4d328ad7e";
    finalImageName = "registry.istio.io/release/ztunnel";
    finalImageTag = "1.30.0-rc.0";
    archiveHash = "sha256-si/XGIUvSOAPwTd0GCezeiKxBDT2GnCNWrHuNNts5ws=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "istio-system"; name = "ztunnel"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "istio-system"; name = "ztunnel"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-networking"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "istio-system"; name = "ztunnel"; }
    ];
  }
  {
    imageName = "registry.k8s.io/external-dns/external-dns";
    imageDigest = "sha256:f53faaf71cb270d1ca9dce6ea0c94bfebf1a18696263487f0fbc74b9bf2bd7ff";
    finalImageName = "registry.k8s.io/external-dns/external-dns";
    finalImageTag = "v0.21.0";
    archiveHash = "sha256-K7UZeshz6Pe2nLWENwfOwleQY7s0dZbCt5h0RmqsEg4=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-foundation"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "external-dns-system"; name = "external-dns"; }
    ];
  }
  {
    imageName = "registry.k8s.io/kube-state-metrics/kube-state-metrics";
    imageDigest = "sha256:1545919b72e3ae035454fc054131e8d0f14b42ef6fc5b2ad5c751cafa6b2130e";
    finalImageName = "registry.k8s.io/kube-state-metrics/kube-state-metrics";
    finalImageTag = "v2.18.0";
    archiveHash = "sha256-gSj8cOXfXbd3JZlbMcdCeX6m+StugUaLdO4uokNtPPo=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-monitoring"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack-kube-state-metrics"; }
    ];
  }
  {
    imageName = "registry.k8s.io/kubectl";
    imageDigest = "sha256:497d298f891edb7608dfce9dae4bb08dffc4ddcd7f5d24a0512d4bbf33e04f26";
    finalImageName = "registry.k8s.io/kubectl";
    finalImageTag = "v1.34.0";
    archiveHash = "sha256-7dOzMbF6gXpX6Bv65fVzW4DqLgpLgoGvZSIjYihmxEQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-monitoring"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Job"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack-victoria-metrics-operator-cleanup-hook"; }
    ];
  }
  {
    imageName = "victoriametrics/operator";
    imageDigest = "sha256:fb5ebef9cba3746d73ee0dee1bb9e4bc80539687518fd1e2e6ab7776b438048a";
    finalImageName = "docker.io/victoriametrics/operator";
    finalImageTag = "v0.70.1";
    archiveHash = "sha256-rb277HtbVnGZMfd9U4tITUCPNzEo1Txwy4aRmSglDIY=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers-monitoring"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack-victoria-metrics-operator"; }
    ];
  }
]
