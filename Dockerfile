# RunPod'un resmi ComfyUI şablonu (PyTorch + CUDA uyumu garanti)
FROM runpod/worker-comfyui:5.9.0-base

# SCAIL-2, SAM3 ve diğer iş akışları için gereken eklentiler
RUN comfy-node-install \
    ComfyUI-AnimateDiff-Evolved \
    ComfyUI-VideoHelperSuite \
    comfyui_controlnet_aux \
    ComfyUI_IPAdapter_plus

# WanVideo Wrapper (SCAIL-2 için gerekli)
WORKDIR /comfyui/custom_nodes
RUN git clone https://github.com/Kijai/ComfyUI-WanVideoWrapper.git && \
    cd ComfyUI-WanVideoWrapper && \
    pip install -r requirements.txt || true
