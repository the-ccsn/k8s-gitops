[
  {
    imageName = "adyanth/cloudflare-operator";
    imageDigest = "sha256:6b168dc237d50e3d36cc5df86bf2be7981700a49d7a4ae02548f4762ec0d7aaa";
    finalImageName = "adyanth/cloudflare-operator";
    finalImageTag = "0.13.1";
    archiveHash = "sha256-vkwQS4n598On1JgF86sbk0gLNuSvK+EmnMqCI4u3enA=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "cloudflare-operator-system"; name = "cloudflare-operator-controller-manager"; }
    ];
  }
  {
    imageName = "cloudflare/cloudflared";
    imageDigest = "sha256:59bab8d3aceec09bf6bdb07d6beca0225ca5cd7ab79436a87ea97978fe1dc4f9";
    finalImageName = "cloudflare/cloudflared";
    finalImageTag = "2026.5.0";
    archiveHash = "sha256-FpaPCgFbDip5MAOAfgzRQJUg0SlFvYb4ZsCijIt2n4I=";
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
    imageDigest = "sha256:32a13f6693a278261e9c9cb7eb606c5e2aa021308ae44fdc73225755048500a8";
    finalImageName = "docker.io/goharbor/harbor-core";
    finalImageTag = "v2.15.0";
    archiveHash = "sha256-mFIV+IJThxf2FozA32fRJlHTgEuYO41EhJQef1/x3CE=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-core"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-jobservice";
    imageDigest = "sha256:a22c7cccba4673b26ffb96f5c37971d85d879dd837bc82448e01c0170b68cf28";
    finalImageName = "docker.io/goharbor/harbor-jobservice";
    finalImageTag = "v2.15.0";
    archiveHash = "sha256-on4jWaFqryMmUjv0H0bhJzHb7Z0a+ZzdZB49Z0J1dro=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-jobservice"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-portal";
    imageDigest = "sha256:541d5fa95bf77240d46a438f86245cdfd6afa6dd7fdd0cf4dd4c905af6a980b1";
    finalImageName = "docker.io/goharbor/harbor-portal";
    finalImageTag = "v2.15.0";
    archiveHash = "sha256-qfBWzTA4uxYz5VaO/ybMeaRw/InJn8nGQyY1MLF4IN0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-portal"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/harbor-registryctl";
    imageDigest = "sha256:463172f71d3a1e8d4f9e3b4e687a447f41fbc3126316d8c150dba04a903bbc47";
    finalImageName = "docker.io/goharbor/harbor-registryctl";
    finalImageTag = "v2.15.0";
    archiveHash = "sha256-/Wa/r2d+2STvKetx6eb1Ky5rYI8tQutgVtmAJBN5pPs=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-registry"; }
    ];
  }
  {
    imageName = "docker.io/goharbor/registry-photon";
    imageDigest = "sha256:beb49fd16cf0906c04a2bf51a22f7210289e7cc2ae43a733e2a0364380aceae6";
    finalImageName = "docker.io/goharbor/registry-photon";
    finalImageTag = "v2.15.0";
    archiveHash = "sha256-tzXvd6xJECembGu1kaCLTwzDQjVt5MQUreGfsukmWNc=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "harbor"; name = "harbor-registry"; }
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
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
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
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "grafana-operator"; name = "grafana-operator"; }
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
    imageName = "ghcr.io/sagernet/sing-box";
    imageDigest = "sha256:da0e2331395c9025a85fa58892772b4cdbe5f2e530e93defeec3968175d06c6d";
    finalImageName = "ghcr.io/sagernet/sing-box";
    finalImageTag = "v1.13.12";
    archiveHash = "sha256-ADuYPHGPIlR6Krx0VT0TYSsuicKWKYDIv14IWvixPYk=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "egress-system"; name = "proxy-engine"; }
    ];
  }
  {
    imageName = "mendhak/http-https-echo";
    imageDigest = "sha256:d072446da821a767d05dc19fa5ab6a27b1150bfb5c6ecfaecf3a2e5f9812794c";
    finalImageName = "mendhak/http-https-echo";
    finalImageTag = "40";
    archiveHash = "sha256-3ZPysAQ70H9HRe+PB9J0AxTaVKZAsMKUO5qbStf+amc=";
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
    finalImageName = "nginx";
    finalImageTag = "mainline-alpine";
    archiveHash = "sha256-NaFxZCvwKOt2OyV8B7znm4kmjhXBqZPq70PT/7REscU=";
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
      { kind = "Deployment"; namespace = "319-reroute"; name = "319-reroute-proxy"; }
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
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
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
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
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
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "kubevirt"; name = "virt-operator"; }
    ];
  }
  {
    imageName = "quay.io/oauth2-proxy/oauth2-proxy";
    imageDigest = "sha256:aa0bd8dd5ab0c78e4c91c92755ad573a5f92241f88138b4141b8ec803463b4fd";
    finalImageName = "quay.io/oauth2-proxy/oauth2-proxy";
    finalImageTag = "v7.15.2";
    archiveHash = "sha256-oMGYyqPjF5RyzlQ+x1+8VaFaC59YWBkuii79QtBpPOs=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "oauth2-proxy"; name = "oauth2-proxy"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "oauth2-proxy"; name = "oauth2-proxy"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "oauth2-proxy"; name = "oauth2-proxy"; }
    ];
  }
  {
    imageName = "rancher/kubectl";
    imageDigest = "sha256:05d2b313e2f397e0ade252136aed47abd72d56ead11d1b027ac70f66362c8495";
    finalImageName = "rancher/kubectl";
    finalImageTag = "v1.36.0";
    archiveHash = "sha256-O5J+4flgyvDqE2mvAJoV9nSO3S1PhXW3ud8mKPjRpoc=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "CronJob"; namespace = "egress-system"; name = "proxy-engine-daily-restarter"; }
    ];
  }
  {
    imageName = "registry-1.docker.io/bitnami/redis-exporter";
    imageDigest = "sha256:3326f940f59cd06f0a96aeca2ab78c02b1dd2fd209a8d52b0317c4c3a24530b1";
    finalImageName = "registry-1.docker.io/bitnami/redis-exporter";
    finalImageTag = "latest";
    archiveHash = "sha256-V8SexXt+5SgJE2APQOtMND/H7M+tvtFbjfYahXnxBQc=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "StatefulSet"; namespace = "harbor"; name = "harbor-redis-master"; }
    ];
  }
  {
    imageName = "registry-1.docker.io/bitnami/redis";
    imageDigest = "sha256:1347d526ecec0c6537e99eac09e7c3405c21664f6044ff60e78b0898da37abd2";
    finalImageName = "registry-1.docker.io/bitnami/redis";
    finalImageTag = "latest";
    archiveHash = "sha256-/TUHolOlho3654jwbAabp0cXehl2AHwPnBbB3h/48bQ=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "harbor"; name = "harbor-redis"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "StatefulSet"; namespace = "harbor"; name = "harbor-redis-master"; }
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
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "istio-system"; name = "istiod"; }
    ];
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
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
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
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Job"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack-victoria-metrics-operator-cleanup-hook"; }
    ];
  }
  {
    imageName = "squat/generic-device-plugin";
    imageDigest = "sha256:66c8d5c270eb2b721f1064c549b9b7898152a6d2f0163380a5d37dc7636c20ff";
    finalImageName = "squat/generic-device-plugin";
    finalImageTag = "0.2.0";
    archiveHash = "sha256-HHbfyNn7/TC6E/6gVq2mP2urLUy+MZdCZmUxYW5yIT0=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
    ];
    sourceChains = [
      [
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "DaemonSet"; namespace = "kube-system"; name = "generic-device-plugin"; }
    ];
  }
  {
    imageName = "victoriametrics/operator";
    imageDigest = "sha256:fb5ebef9cba3746d73ee0dee1bb9e4bc80539687518fd1e2e6ab7776b438048a";
    finalImageName = "victoriametrics/operator";
    finalImageTag = "v0.70.1";
    archiveHash = "sha256-/p8F8uFvV55QDnspaGTsiFYmSSQQrdKHf2Zvv5m0Kpc=";
    os = "linux";
    arch = "amd64";
    sources = [
      { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
    ];
    sourceChains = [
      [
        { kind = "HelmRelease"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack"; }
        { kind = "Kustomization"; namespace = "flux-system"; name = "infra-controllers"; }
      ]
    ];
    targets = [
      { kind = "Deployment"; namespace = "monitoring"; name = "victoria-metrics-k8s-stack-victoria-metrics-operator"; }
    ];
  }
]
