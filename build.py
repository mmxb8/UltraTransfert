"""Compilation du Python et, si disponible, du helper C++ natif."""
import compileall
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent
os.chdir(root)
if not all(compileall.compile_dir(folder, quiet=1) for folder in ("ultra", "research")):
    raise SystemExit("Compilation Python échouée")
(root/"bin").mkdir(exist_ok=True)
if os.name == "nt":
    if shutil.which("cl"):
        subprocess.run(["cl", "/nologo", "/std:c++17", "/EHsc", "/O2", "native/ultra_native.cpp", "/Fe:bin/ultra_native.exe", "bcrypt.lib"], check=True)
    else:
        print("Helper Windows non compilé : compilateur MSVC absent. Le moteur Python reste utilisable.")
else:
    if shutil.which("g++"):
        subprocess.run(["g++", "-std=c++17", "-O3", "-Wall", "-Wextra", "-Werror", "native/ultra_native.cpp", "-o", "bin/ultra_native", "-lcrypto"], check=True)
    else:
        print("Helper natif non compilé : g++ absent.")
