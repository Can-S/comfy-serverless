# 1. Temel İmaj: RunPod'un resmi, boş ComfyUI şablonu (Sadece comfy-cli ve temel araçlar var)
FROM runpod/worker-comfyui:8.4.0-base

# 2. İşletim Sistemi Seviyesi: Root yetkisiyle Blender ve diğer gerekli araçları kuruyoruz
USER root
RUN apt-get update && apt-get install -y \
    blender \
    wget \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Python Bağımlılıkları: RunPod ve API istekleri için gerekli kütüphaneler
RUN pip install runpod huggingface_hub requests

# 4. ComfyUI Eklentileri (Custom Nodes): Projede kullandığımız tüm düğümler
# Not: Yüz koruma (IP-Adapter) eklentisini de şimdiden kuruyoruz.
RUN comfy-node-install \
    ComfyUI-AnimateDiff-Evolved \
    ComfyUI-VideoHelperSuite \
    comfyui_controlnet_aux \
    ComfyUI_IPAdapter_plus

# 5. Kendi yazdığımız dosyaları imaja kopyalıyoruz
COPY src/blender_extract.py /blender_extract.py
COPY src/handler.py /handler.py
COPY src/workflow_api.json /workflow_api.json

# 6. Çalışma dizinini ayarlıyoruz
WORKDIR /

# 7. Sunucu uyandığında (Cold Start) çalışacak ana kodumuzu belirliyoruz
CMD ["python3", "-u", "/handler.py"]
