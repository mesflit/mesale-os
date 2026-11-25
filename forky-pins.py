#!/usr/bin/python3
"""Kökte kurulu olup yalnızca Debian testing'de (forky) bulunan sürümlerin kaynak paketlerini yazar."""
import glob, re, subprocess
def read(pat):
    s = set()
    for f in glob.glob("/var/lib/apt/lists/" + pat):
        for b in subprocess.run(["/usr/lib/apt/apt-helper", "cat-file", f], capture_output=True, text=True).stdout.split("\n\n"):
            p, v = re.search(r"^Package: (.*)", b, re.M), re.search(r"^Version: (.*)", b, re.M)
            if p and v: s.add((p[1], v[1]))
    return s
stable, forky = read("*trixie*Packages*"), read("*_forky_*Packages*")
assert stable and forky, "apt listeleri okunamadı"
out = set()
for l in subprocess.run(["dpkg-query", "-W", "-f", "${Package} ${Version} ${source:Package}\n"], capture_output=True, text=True).stdout.splitlines():
    p, v, s = l.split()
    if (p, v) in forky and (p, v) not in stable: out.add("src:" + s)
print(" ".join(sorted(out)))
