#!/usr/bin/python3
"""Print the source packages whose installed version exists only in Debian testing."""
import glob
import re
import subprocess

LISTS = "/var/lib/apt/lists/"


def read_index(pattern):
    found = set()
    for path in glob.glob(LISTS + pattern):
        text = subprocess.run(["/usr/lib/apt/apt-helper", "cat-file", path],
                              capture_output=True, text=True, check=True).stdout
        for block in text.split("\n\n"):
            name = re.search(r"^Package: (.*)", block, re.M)
            version = re.search(r"^Version: (.*)", block, re.M)
            if name and version:
                found.add((name[1], version[1]))
    return found


stable, testing = read_index("*trixie*Packages*"), read_index("*_forky_*Packages*")
assert stable and testing, "could not read the apt lists"

installed = subprocess.run(["dpkg-query", "-W", "-f", "${Package} ${Version} ${source:Package}\n"],
                           capture_output=True, text=True, check=True).stdout
sources = set()
for line in installed.splitlines():
    name, version, source = line.split()
    if (name, version) in testing and (name, version) not in stable:
        sources.add(f"src:{source}")
print(" ".join(sorted(sources)))
