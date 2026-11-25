# Wallpapers, logo, boot images: all generated from code.
{
  runCommand,
  python3,
  librsvg,
  inter,
  makeFontsConf,
}:
runCommand "mesale-artwork"
  {
    nativeBuildInputs = [
      (python3.withPackages (p: [
        p.numpy
        p.pillow
      ]))
      librsvg
    ];
    FONTCONFIG_FILE = makeFontsConf { fontDirectories = [ inter ]; };
    PYTHONDONTWRITEBYTECODE = 1;
  }
  ''
    export XDG_CACHE_HOME=$TMPDIR
    python3 ${../artwork}/generate.py $out
  ''
