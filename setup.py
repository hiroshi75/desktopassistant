from setuptools import setup, find_packages

setup(
    name="desktopassistant",
    version="0.1.0",
    packages=["desktopassistant"],  # 明示的にパッケージを指定
    install_requires=[
        "fastapi",
        "langchain_aws",
        "markdown",
        "amazon-transcribe",
        "vosk",
        "pyaudio",
        "uvicorn",
        "websockets",
        "numpy",
        "pywebview",
        "Pillow",
        "pystray"
    ],
)
