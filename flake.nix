{
  description = "k8s-gitops image lock generator";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }:
    let
      forAllSystems = f:
        nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" ] (
          system: f (import nixpkgs { inherit system; })
        );
      clustersDir = ./clusters;
      clusterNames =
        if builtins.pathExists clustersDir then
          builtins.attrNames (
            nixpkgs.lib.filterAttrs (_name: ty: ty == "directory") (builtins.readDir clustersDir)
          )
        else
          [ ];
      mkName = cluster: "gen-image-lock-${cluster}";
    in {
      lib = {
        mkMultiArchImageArchive = import ./lib/mkMultiArchImageArchive.nix;
      };

      packages = forAllSystems (pkgs: {
        gen-image-lock = pkgs.writeShellApplication {
          name = "gen-image-lock";
          runtimeInputs = with pkgs; [
            kustomize
            kubernetes-helm
            crane
            uv
            fluxcd
            skopeo
            nix
            git
            bash
          ];
          text = ''
            exec uv run ${./scripts/gen-image-lock.py} \
              --extra-images-annotation image-lock/extra-images \
              "$@"
          '';
        };
      }
      // builtins.listToAttrs (
        map (
          cluster:
          let
            wrappedName = mkName cluster;
            system = pkgs.stdenv.hostPlatform.system;
          in
          {
            name = wrappedName;
            value = pkgs.writeShellApplication {
              name = wrappedName;
              runtimeInputs = [ self.packages.${system}.gen-image-lock ];
              text = ''
                exec gen-image-lock \
                  --cluster ${pkgs.lib.escapeShellArg cluster} \
                  --extra-images-annotation image-lock/extra-images \
                  "$@"
              '';
            };
          }
        ) clusterNames
      )
      // {
        gen-image-lock-all = pkgs.writeShellApplication {
          name = "gen-image-lock-all";
          runtimeInputs = [ self.packages.${pkgs.stdenv.hostPlatform.system}.gen-image-lock ];
          text = ''
            set -euo pipefail
            COMMIT_MSG_FILE=""
            REPORT_FILE=""
            args=()
            
            while [[ $# -gt 0 ]]; do
              case "$1" in
                --commit-msg-file) COMMIT_MSG_FILE="$2"; shift 2 ;;
                --report-file) REPORT_FILE="$2"; shift 2 ;;
                *) args+=("$1"); shift ;;
              esac
            done

            clusters=(${pkgs.lib.concatStringsSep " " (map pkgs.lib.escapeShellArg clusterNames)})
            for cluster in "''${clusters[@]}"; do
              echo "Processing $cluster..."
              gen-image-lock --cluster "$cluster" \
                --extra-images-annotation image-lock/extra-images \
                "''${args[@]}" \
                --commit-msg-file "msg_$cluster.txt" \
                --report-file "rep_$cluster.md"
              
              if [[ -n "$COMMIT_MSG_FILE" && -f "msg_$cluster.txt" ]]; then
                cat "msg_$cluster.txt" >> "$COMMIT_MSG_FILE"
                echo -e "\n\n" >> "$COMMIT_MSG_FILE"
                rm "msg_$cluster.txt"
              fi

              if [[ -n "$REPORT_FILE" && -f "rep_$cluster.md" ]]; then
                cat "rep_$cluster.md" >> "$REPORT_FILE"
                echo -e "\n---\n" >> "$REPORT_FILE"
                rm "rep_$cluster.md"
              fi
            done
          '';
        };
      });

      apps = forAllSystems (pkgs:
        let
          system = pkgs.stdenv.hostPlatform.system;
        in
        {
          gen-image-lock = {
            type = "app";
            program = "${self.packages.${system}.gen-image-lock}/bin/gen-image-lock";
          };
          gen-image-lock-all = {
            type = "app";
            program = "${self.packages.${system}.gen-image-lock-all}/bin/gen-image-lock-all";
          };
        }
        // builtins.listToAttrs (
          map (
            cluster:
            let
              wrappedName = mkName cluster;
            in
            {
              name = wrappedName;
              value = {
                type = "app";
                program = "${self.packages.${system}.${wrappedName}}/bin/${wrappedName}";
              };
            }
          ) clusterNames
        ));

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          name = "k8s-gitops";
          packages = with pkgs; [ bashInteractive ];
        };
      });
    };
}
