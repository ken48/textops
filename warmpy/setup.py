from pathlib import Path
import json
from setuptools import setup

APP = ["main.py"]

includes_path = Path(".build/extra_includes.json")
includes = json.loads(includes_path.read_text("utf-8")) if includes_path.exists() else []

OPTIONS = {
    "argv_emulation": False,
    "packages": ["host"],
    "includes": includes,
    "resources": [
        ".build/warmup.json",
        "assets/warmpyStatusTemplate.png",
        "assets/warmpyStatusTemplate@2x.png",
    ],
    "iconfile": "assets/warmpy.icns",
    "plist": {
        "CFBundleName": "warmpy",
        "CFBundleDisplayName": "warmpy",
        "LSUIElement": True,
    },
    "dist_dir": ".build/dist",
    "bdist_base": ".build/build",
    "alias": False,
    "site_packages": False,
    "use_pythonpath": False,
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
