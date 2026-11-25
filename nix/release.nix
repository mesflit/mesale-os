# VERSION and CODENAME from config/mesale.conf, so they are defined once.
{ lib }:
let
  text = builtins.readFile ../config/mesale.conf;
  value =
    key:
    let
      line = lib.findFirst (lib.hasPrefix "${key}=") (throw "${key} missing") (lib.splitString "\n" text);
    in
    lib.removeSuffix "\"" (lib.removePrefix "\"" (lib.removePrefix "${key}=" line));
in
{
  version = value "VERSION";
  codename = value "CODENAME";
}
