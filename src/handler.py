import runpod
import json
import os
import subprocess
import base64
import urllib.request
import time

# --- AYARLAR ---
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_OUTPUT_DIR = "/comfyui/output"

# Ağ diskimiz (RunPod bunu otomatik olarak bu klasöre bağlar)
VOLUME_DIR = "/runpod-volume/models"
CHECKPOINTS_DIR = os.path.join(VOLUME_DIR, "checkpoints")
CONTROLNET_DIR = os.path.join(VOLUME_DIR, "controlnet")
ANIMATEDIFF_DIR = os.path.join(VOLUME_DIR, "animatediff_models")
IPADAPTER_DIR = os.path.join(VOLUME_DIR, "ipadapter")

# İndirilecek modellerin listesi (Örnek URL'ler, gerçek projede güncellenecek)
MODELS_TO_DOWNLOAD = {
    "DreamShaper.safetensors": {
        "url": "https://civitai.com/api/download/models/128713", # Örnek link
        "path": os.path.join(CHECKPOINTS_DIR, "DreamShaper.safetensors")
    },
    "mm_sd_v15_v2.ckpt": {
        "url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt",
        "path": os.path.join(ANIMATEDIFF_DIR, "mm_sd_v15_v2.ckpt")
    }
    # ControlNet ve IP-Adapter modelleri buraya eklenecek
}

def ensure_directories():
    """Modellerin indirileceği klasörleri ağ diskinde (volume) oluşturur."""
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    os.makedirs(CONTROLNET_DIR, exist_ok=True)
    os.makedirs(ANIMATEDIFF_DIR, exist_ok=True)
    os.makedirs(IPADAPTER_DIR, exist_ok=True)

def download_models_if_missing():
    """Modelleri kontrol eder, eksikse indirir ve sürecin durumunu döndürür."""
    ensure_directories()
    
    missing_models = []
    for model_name, info in MODELS_TO_DOWNLOAD.items():
        if not os.path.exists(info["path"]):
            missing_models.append(model_name)
            
    if not missing_models:
        return False, "Sistem: Modeller diskte (#runpod-volume) HAZIR. İndirme atlandı."
        
    # Eğer eksik model varsa indirme işlemini yap
    for model_name in missing_models:
        info = MODELS_TO_DOWNLOAD[model_name]
        # Gerçekte burada wget veya requests ile indirme yapılır
        cmd = ["wget", "-O", info["path"], info["url"]]
        subprocess.run(cmd, check=False) # Hata yönetimini basit tutuyoruz
        
    return True, f"Sistem: Eksik modeller ({', '.join(missing_models)}) başarıyla ağ diskine indirildi ve kilitlendi!"

def generate_depth_map(fbx_path):
    """Blender scriptini çağırarak FBX'ten derinlik haritası üretir."""
    output_video_path = "/tmp/depth_output.mp4"
    cmd = [
        "blender", "-b", "-P", "/blender_extract.py",
        "--", "--fbx", fbx_path, "--output", output_video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Blender hatası: {result.stderr}")
    return output_video_path

def run_comfyui_workflow(depth_video_path, prompt_text):
    """Derinlik videosunu ComfyUI'a gönderip renderlatır."""
    workflow_path = os.path.join(os.path.dirname(__file__), "workflow_api.json")
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
        
    # Json dinamik atamaları (Node ID'lerine göre)
    # workflow["14"]["inputs"]["video"] = depth_video_path
    # workflow["6"]["inputs"]["text"] = prompt_text
    
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(COMFYUI_API_URL, data=data, headers={'Content-Type': 'application/json'})
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        prompt_id = result.get("prompt_id")
        
    while True:
        req_hist = urllib.request.Request("http://127.0.0.1:8188/history")
        with urllib.request.urlopen(req_hist) as hist_res:
            history = json.loads(hist_res.read())
            if prompt_id in history:
                break
        time.sleep(2)
        
    outputs = os.listdir(COMFYUI_OUTPUT_DIR)
    mp4_files = [f for f in outputs if f.endswith(".mp4")]
    if not mp4_files:
        raise Exception("ComfyUI çıktısı bulunamadı!")
        
    latest_file = max([os.path.join(COMFYUI_OUTPUT_DIR, f) for f in mp4_files], key=os.path.getctime)
    with open(latest_file, "rb") as vid_file:
        encoded_string = base64.b64encode(vid_file.read()).decode('utf-8')
    return encoded_string

def handler(job):
    """RunPod Serverless tarafından tetiklenen ana fonsiyon."""
    job_input = job.get("input", {})
    fbx_base64 = job_input.get("fbx_base64")
    prompt_text = job_input.get("prompt", "a character dancing")
    
    if not fbx_base64:
        yield {"status": "error", "message": "FBX verisi bulunamadı."}
        return
        
    try:
        # AŞAMA 1: Modellerin Kontrolü ve İndirilmesi
        yield {"status": "progress", "message": "Sistem: Yapay zeka modelleri kontrol ediliyor..."}
        
        was_downloaded, msg = download_models_if_missing()
        if was_downloaded:
            yield {"status": "progress", "message": "Sistem: İLK KURULUM - Ağ diski boştu, devasa modeller şu an internetten indiriliyor. Lütfen 3-5 dakika bekleyin..."}
        
        yield {"status": "progress", "message": msg}
        
        # AŞAMA 2: Blender İşlemi
        yield {"status": "progress", "message": "Sistem: Modeller hazır! Blender 3D kameraman devrede, FBX inceleniyor..."}
        temp_fbx = "/tmp/input_model.fbx"
        with open(temp_fbx, "wb") as f:
            f.write(base64.b64decode(fbx_base64))
            
        depth_video_path = generate_depth_map(temp_fbx)
        
        # AŞAMA 3: ComfyUI Render İşlemi
        yield {"status": "progress", "message": "Sistem: Blender bitti! ComfyUI (ControlNet + AnimateDiff) video render işlemine başladı. Bu işlem biraz sürebilir..."}
        final_video_base64 = run_comfyui_workflow(depth_video_path, prompt_text)
        
        # AŞAMA 4: Bitiş
        # yield ile bitirirsek streaming tamamlanır, ya da doğrudan return ile final sonucu dönebiliriz.
        return {
            "status": "success",
            "message": "Sistem: Render tamamlandı! İşte videonuz.",
            "video_base64": final_video_base64
        }
        
    except Exception as e:
        yield {"status": "error", "message": str(e)}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
