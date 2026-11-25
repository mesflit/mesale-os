# The website, generated from the same files the OS is built from.
{
  runCommand,
  callPackage,
  python3,
  imagemagick,
  woff2,
  inter,
  artwork,
  video,
}:
let
  release = callPackage ./release.nix { };
in
runCommand "mesale-website"
  {
    nativeBuildInputs = [
      python3
      imagemagick
      woff2
    ];
  }
  ''
    mkdir -p $out/img $out/fonts
    cp ${../website}/static/* $out/
    cp ${../packages/mesale-desktop/usr/share/gnome-shell/extensions}/mesale-shell@mesale/calculator.js $out/calculator.js
    for w in ${artwork}/usr/share/backgrounds/mesale/*.jpg; do
      name=$(basename $w .jpg)
      magick $w -resize 2400x -quality 92 $out/img/$name.webp
      magick $w -resize 480x -quality 90 $out/img/$name-thumb.webp
    done
    for s in ${../website}/screenshots/*.png; do
      [ -e "$s" ] || continue
      magick "$s" -quality 88 $out/img/$(basename "$s" .png).webp
    done
    magick $out/img/day.webp -resize 1200x630^ -gravity center -extent 1200x630 -quality 85 $out/img/social.jpg
    cp -r ${video} $out/video
    cp ${artwork}/usr/share/icons/hicolor/scalable/apps/mesale-{logo,flame}.svg $out/img/
    cp ${inter}/share/fonts/truetype/InterVariable.ttf inter.ttf
    woff2_compress inter.ttf
    cp inter.woff2 $out/fonts/

    python3 ${../website}/generate.py \
      --features ${../packages/mesale-base/usr/lib/mesale/features} \
      --looks ${artwork}/usr/share/mesale/looks.json \
      --screenshots ${../website}/screenshots \
      --version "${release.version}" --codename "${release.codename}" \
      --template ${../website}/template.html >$out/index.html
  ''
