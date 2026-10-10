{ clangStdenv, fetchurl, pcre2, binutils }:

let
  addonSource = builtins.path {
    path = ./.;
    name = "ccsn-nginx-server-timing-source";
    filter = path: type:
      type == "directory"
      || builtins.elem (builtins.baseNameOf path) [
        "config"
        "ngx_http_ccsn_server_timing_module.c"
      ];
  };
in
clangStdenv.mkDerivation {
  pname = "nginx-server-timing-module";
  version = "1.29.8";

  src = fetchurl {
    url = "https://nginx.org/download/nginx-1.29.8.tar.gz";
    sha256 = "7f1b985dace8fe706dfc288b83927c928f0ae60bcb7507c2d4e0025eca7280c3";
  };

  strictDeps = true;
  nativeBuildInputs = [ binutils ];
  buildInputs = [ pcre2 ];

  configurePhase = ''
    runHook preConfigure
    ./configure \
      --with-compat \
      --without-http_gzip_module \
      --add-dynamic-module=${addonSource} \
      --with-cc-opt=-O3
    runHook postConfigure
  '';

  buildPhase = ''
    runHook preBuild
    make -f objs/Makefile modules LINK="$CC -nostdlib"
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/lib/nginx/modules"
    cp objs/ngx_http_ccsn_server_timing_module.so "$out/lib/nginx/modules/"
    if readelf -d "$out/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so" | \
      grep -q '(NEEDED)'; then
      echo "The module must resolve libc through the pinned Nginx executable" >&2
      exit 1
    fi
    runHook postInstall
  '';

  meta.platforms = [ "x86_64-linux" "aarch64-linux" ];
}
