from setuptools import setup, Extension

video = Extension(
    name="ardrone.video",
    libraries=["avcodec", "avformat", "avutil", "swscale"],
    sources=["ardrone/video.c"],
)

setup(ext_modules=[video])
