import os
from setuptools import setup, Extension

delete_path = "src/timerc/timerc.cp314-win_amd64.pyd"
if os.path.exists(delete_path):
    os.remove(delete_path)

module = Extension("timerc", sources=["src/timerc/timerc.c"])

setup(
    name="timerc",
    version="1.0",
    description="Test c ext",
    ext_modules=[module],
    options={
        "build_ext": {"build_lib": "src/timerc/", "build_temp": "src/timerc/.build/"}
    },
)
