import os
from huggingface_hub import hf_hub_download

# RunPod'da kalıcı ağ diskinin bağlandığı yer genelde /workspace'tir.
# Eğer lokalde test ediyorsanız bilgisayarınızda "models" adında bir klasör açar.
BASE_MODEL_DIR = os.environ.get("MODEL_DIR", "./models")

# İndirilecek modellerin listesi (Örnek olarak ControlNet Depth modeli eklendi)
MODELS_TO_DOWNLOAD = [
    {
        "repo_id": "lllyasviel/ControlNet-v1-1",
        "filename": "control_v11p_sd15_depth.pth",
        "subfolder": "controlnet" # ComfyUI'da modellerin duracağı alt klasör
    }
    # İleride buraya AnimateDiff ve IP-Adapter modellerini de ekleyeceğiz.
]

def download_models():
    print(f"[*] Modeller kontrol ediliyor. Hedef dizin: {BASE_MODEL_DIR}")
    
    for model in MODELS_TO_DOWNLOAD:
        target_dir = os.path.join(BASE_MODEL_DIR, model["subfolder"])
        os.makedirs(target_dir, exist_ok=True)
        
        print(f"[-] Kontrol ediliyor: {model['filename']}")
        
        # hf_hub_download, dosya daha önce indirilmişse tekrar indirmez, çok akıllıdır.
        hf_hub_download(
            repo_id=model["repo_id"],
            filename=model["filename"],
            local_dir=target_dir,
            local_dir_use_symlinks=False
        )
        
    print("[+] Tüm modeller başarıyla hazırlandı!")

if __name__ == "__main__":
    download_models()
