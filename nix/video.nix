# The film on the website, rendered from HTML with the real artwork and screenshots.
{
  runCommand,
  python3,
  playwright-driver,
  ffmpeg-headless,
  imagemagick,
  inter,
  makeFontsConf,
  artwork,
}:
runCommand "mesale-video"
  {
    nativeBuildInputs = [
      (python3.withPackages (p: [ p.playwright ]))
      ffmpeg-headless
      imagemagick
    ];
    FONTCONFIG_FILE = makeFontsConf { fontDirectories = [ inter ]; };
    PLAYWRIGHT_BROWSERS_PATH = playwright-driver.browsers;
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = "true";
  }
  ''
    export HOME=$TMPDIR
    cp -r --no-preserve=mode ${../website/video} film
    mkdir film/assets
    for look in night dusk dawn mist day; do
      magick ${artwork}/usr/share/backgrounds/mesale/$look.jpg -resize 1440x -quality 94 film/assets/$look.jpg
    done
    cp ${../website/screenshots}/{desktop,center}.png film/assets/
    cp ${artwork}/usr/share/icons/hicolor/scalable/apps/mesale-flame.svg film/assets/flame.svg
    python3 ${../website/generate.py} --film-features ${../packages/mesale-base/usr/lib/mesale/features} >film/features.js

    mkdir $out
    python3 film/render.py film 30 |
      ffmpeg -loglevel error -f image2pipe -framerate 30 -c:v mjpeg -i - \
        -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart $out/mesale.mp4
    ffmpeg -loglevel error -ss 7.9 -i $out/mesale.mp4 -frames:v 1 -q:v 3 $out/poster.jpg
  ''
