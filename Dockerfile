# 1. Temel İmaj: RunPod'un resmi, boş ComfyUI şablonu
FROM runpod/worker-comfyui:5.9.0-base

USER root
RUN apt-get update && apt-get install -y \
    blender \
    wget \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install runpod huggingface_hub requests

# ComfyUI'ın en güncel sürümüne geçiyoruz (SCAIL-2 Subgraph desteği için PR#14373 gerekli)
WORKDIR /comfyui
RUN git pull origin master
# Güncel ComfyUI'ın bağımlılıklarını (özellikle comfy-kitchen) zorla güncelliyoruz:
RUN pip install --upgrade -r requirements.txt

# Klasik eklentilerimiz
RUN comfy-node-install \
    ComfyUI-AnimateDiff-Evolved \
    ComfyUI-VideoHelperSuite \
    comfyui_controlnet_aux \
    ComfyUI_IPAdapter_plus

# WanVideo ve SCAIL-2 eklentilerini (Kijai Wrapper) manuel olarak kuruyoruz
WORKDIR /comfyui/custom_nodes
RUN git clone https://github.com/Kijai/ComfyUI-WanVideoWrapper.git || true
WORKDIR /comfyui/custom_nodes/ComfyUI-WanVideoWrapper
RUN pip install -r requirements.txt || true
# Gerekirse diğer SCAIL-2/SAM3 node'ları buraya eklenebilir

WORKDIR /
COPY src/blender_extract.py /blender_extract.py
COPY src/handler.py /handler.py
COPY src/workflow_api.json /workflow_api.json

CMD ["python3", "-u", "/handler.py"]
