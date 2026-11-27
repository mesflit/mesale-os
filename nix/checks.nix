# nix flake check
{
  runCommand,
  shellcheck,
  nodejs,
  python3,
  artwork,
  debs,
}:
{
  inherit artwork debs;

  shell = runCommand "check-shell" { nativeBuildInputs = [ shellcheck ]; } ''
    cd ${../.}
    shellcheck -x -S warning -e SC1090,SC1091,SC2034,SC2086,SC2154 build/build.sh build/lib/*.sh config/*.sh config/mesale.conf tools/*.sh -s bash
    touch $out
  '';

  javascript = runCommand "check-javascript" { nativeBuildInputs = [ nodejs ]; } ''
    for f in ${../packages/mesale-desktop/usr/share/gnome-shell/extensions}/*/*.js ${../website/static}/*.js; do
      cat "$f" >file.mjs
      node --check file.mjs
    done
    touch $out
  '';

  python = runCommand "check-python" { nativeBuildInputs = [ python3 ]; } ''
    cd ${../.}
    for f in $(find . -name '*.py') packages/mesale-live/usr/lib/mesale/installer-options; do
      python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$f"
    done
    HOME=$TMPDIR python3 -m unittest discover -s tests/play
    touch $out
  '';
}
