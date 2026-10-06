#!/usr/bin/env bash

# Copy from https://github.com/fluxcd/flux2-kustomize-helm-example/blob/main/scripts/validate.sh

# This script downloads the Flux OpenAPI schemas, then it validates the
# Flux custom resources and the kustomize overlays using kubeconform.
# This script is meant to be run locally and in CI before the changes
# are merged on the main branch that's synced by Flux.

# Copyright 2023 The Flux authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Prerequisites
# - yq v4.34
# - kustomize v5.3
# - kubeconform v0.6

set -o errexit
set -o pipefail

strict_missing_schemas="${STRICT_MISSING_SCHEMAS:-false}"
schema_report_file="/tmp/kubeconform-schema-report.log"
rm -f "$schema_report_file"

# mirror kustomize-controller build options
kustomize_flags=("--load-restrictor=LoadRestrictionsNone")
kustomize_config="kustomization.yaml"

# skip Kubernetes Secrets due to SOPS fields failing validation
kubeconform_flags=("-skip=Secret")
kubeconform_config=(
  "-strict"
  "-ignore-missing-schemas"
  "-schema-location" "/tmp/cilium-crd-schemas/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"
  "-schema-location" "default"
  "-schema-location" "/tmp/flux-crd-schemas"
  "-schema-location" "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"
  "-summary"
  "-verbose"
)

echo "INFO - Downloading Flux OpenAPI schemas"
mkdir -p /tmp/flux-crd-schemas/master-standalone-strict
curl -sL https://github.com/fluxcd/flux2/releases/latest/download/crd-schemas.tar.gz | tar zxf - -C /tmp/flux-crd-schemas/master-standalone-strict

# The catalog's BGP peer schema predates sourceInterface. Validate against the
# official CRD from the Cilium version selected by this cluster instead.
cilium_version="$(yq -r '.spec.ref.tag' infra/pre-controllers/base/cilium/helm-oci-repo.yaml)"
[[ "$cilium_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
mkdir -p /tmp/cilium-crd-schemas/cilium.io
curl --fail --silent --show-error --location --retry 3 \
  "https://raw.githubusercontent.com/cilium/cilium/v${cilium_version}/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumbgppeerconfigs.yaml" | \
  yq -o=json '.spec.versions[] | select(.name == "v2") | .schema.openAPIV3Schema' \
    > /tmp/cilium-crd-schemas/cilium.io/ciliumbgppeerconfig_v2.json

find . -type f -name '*.yaml' -print0 | while IFS= read -r -d $'\0' file;
  do
    echo "INFO - Validating $file"
    yq e 'true' "$file" > /dev/null
done

echo "INFO - Validating clusters"
find ./clusters -maxdepth 2 -type f -name '*.yaml' -print0 | while IFS= read -r -d $'\0' file;
  do
    kubeconform "${kubeconform_flags[@]}" "${kubeconform_config[@]}" "${file}" | tee -a "$schema_report_file"
    if [[ ${PIPESTATUS[0]} != 0 ]]; then
      exit 1
    fi
done

echo "INFO - Validating CRD manifests"
find . -type f -name '*.yaml' -print0 | while IFS= read -r -d $'\0' file;
  do
    if yq e 'select(.kind == "CustomResourceDefinition") | .kind' "$file" 2>/dev/null | grep -q '^CustomResourceDefinition$'; then
      echo "INFO - Validating CRD file $file"
      kubeconform "${kubeconform_flags[@]}" "${kubeconform_config[@]}" "$file" | tee -a "$schema_report_file"
      if [[ ${PIPESTATUS[0]} != 0 ]]; then
        exit 1
      fi
    fi
done

echo "INFO - Validating kustomize overlays"
find . -type f -name $kustomize_config -print0 | while IFS= read -r -d $'\0' file;
  do
    echo "INFO - Validating kustomization ${file/%$kustomize_config}"
    kustomize build "${file/%$kustomize_config}" "${kustomize_flags[@]}" | \
      kubeconform "${kubeconform_flags[@]}" "${kubeconform_config[@]}" | tee -a "$schema_report_file"
    if [[ ${PIPESTATUS[0]} != 0 ]]; then
      exit 1
    fi
done

echo "INFO - Reporting missing schemas"
missing_schema_lines="$(grep -E 'could not find schema for|could not find schema' "$schema_report_file" || true)"
if [[ -n "$missing_schema_lines" ]]; then
  echo "WARN - Some resources are missing schemas in kubeconform sources:"
  printf '%s\n' "$missing_schema_lines" | sed 's/^/  - /'

  if [[ "$strict_missing_schemas" == "true" ]]; then
    echo "ERROR - STRICT_MISSING_SCHEMAS=true and missing schemas were found."
    exit 1
  fi

  echo "INFO - Set STRICT_MISSING_SCHEMAS=true to fail CI on missing schemas."
else
  echo "INFO - No missing schemas found."
fi
