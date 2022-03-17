from setuptools import setup

setup(
    name = 'vidlog',
    version = '0.1',
    description =  "Utility for processing eMiata dashcam video.",
    url = "https://github.com/kroesche/emiata-vidlog",
    author = "Joseph Kroesche",
    license = "MIT",
    python_requires = ">=3.4",
    packages = ["vidlog"],
    install_requires = ['opencv-python', 'ffmpeg-python'],
    entry_points = {
        "console_scripts": [
            "vidlog=vidlog.vidlog:cli"]
    },
    classifiers = [
        "Private :: Do Not Upload"
    ]
)
