import runpod
import json
import os
import subprocess
import base64
import urllib.request
import time

import socket
import sys

# --- AYARLAR ---
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_OUTPUT_DIR = "/comfyui/output"
COMFYUI_INPUT_DIR = "/comfyui/input"
VOLUME_DIR = "/runpod-volume/models"

def start_comfyui():
    print("Sistem: ComfyUI sunucusu başlatılıyor...")
    # ComfyUI'ı arka planda başlat (Logları RunPod paneline yansıtmak için stdout ve stderr'i yönlendiriyoruz)
    subprocess.Popen([sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188"], 
                     cwd="/comfyui", 
                     stdout=sys.stdout, 
                     stderr=sys.stderr)
    
    # Sunucu ayağa kalkana kadar bekle
    for _ in range(120):
        try:
            with socket.create_connection(("127.0.0.1", 8188), timeout=1):
                print("Sistem: ComfyUI sunucusu hazır!")
                return
        except OSError:
            time.sleep(1)
    print("HATA: ComfyUI sunucusu başlatılamadı! (Zaman aşımı)")

start_comfyui()

# Devasa Model Kütüphanesi (JSON'daki isimler ve URL'ler)
MODELS_TO_DOWNLOAD = {
    # Klasik SD1.5 ve AnimateDiff Modelleri
    "DreamShaper.safetensors": {"url": "https://civitai.com/api/download/models/128713", "dir": "checkpoints"},
    "mm_sd_v15_v2.ckpt": {"url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt", "dir": "animatediff_models"},
    
    # SCAIL-2 (Wan 2.1 14B) ve SAM3 Modelleri
    "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors": {"url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors", "dir": "loras"},
    "wan2.1_SCAIL_2_DPO_lora_bf16.safetensors": {"url": "https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/loras/wan2.1_SCAIL_2_DPO_lora_bf16.safetensors", "dir": "loras"},
    "Wan2_1_VAE_bf16.safetensors": {"url": "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors", "dir": "vae"},
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors": {"url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "dir": "text_encoders"},
    "clip_vision_h.safetensors": {"url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors", "dir": "clip_vision"},
    "wan2.1_14B_SCAIL_2_fp16.safetensors": {"url": "https://huggingface.co/Comfy-Org/SCAIL-2/resolve/main/diffusion_models/wan2.1_14B_SCAIL_2_fp16.safetensors", "dir": "diffusion_models"},
    "sam3.1_multiplex_fp16.safetensors": {"url": "https://huggingface.co/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors", "dir": "checkpoints"}
}

def download_models_if_missing(dynamic_models=None):
    """Modelleri Ağ Diskinde kontrol eder ve eksik olanları indirir."""
    # Sabit listemizi kopyala
    models = MODELS_TO_DOWNLOAD.copy()
    
    # Kullanıcı dışarıdan özel model listesi yolladıysa, onları da ekle
    if dynamic_models:
        for model_name, info in dynamic_models.items():
            models[model_name] = info

    missing_models = []
    
    for model_name, info in models.items():
        target_dir = os.path.join(VOLUME_DIR, info["dir"])
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, model_name)
        
        if not os.path.exists(target_path):
            missing_models.append((model_name, info["url"], target_path))
            
    if not missing_models:
        return False, "Sistem: Tüm devasa modeller diskte hazır. İndirme atlandı."
        
    for model_name, url, target_path in missing_models:
        cmd = ["wget", "-O", target_path, url]
        subprocess.run(cmd, check=False)
        
    names = [m[0] for m in missing_models]
    return True, f"Sistem: Eksik modeller başarıyla indirildi: {', '.join(names)}"

def generate_depth_map(fbx_path):
    output_video_path = "/tmp/depth_output.mp4"
    cmd = ["blender", "-b", "-P", "/blender_extract.py", "--", fbx_path, output_video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Blender hatası: {result.stderr}")
    return output_video_path

def run_comfyui_workflow(workflow_json):
    """Verilen JSON haritasını ComfyUI'a gönderip render sonucunu döndürür."""
    data = json.dumps({"prompt": workflow_json}).encode('utf-8')
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
        raise Exception("ComfyUI çıktısı bulunamadı (Video üretilemedi)!")
        
    latest_file = max([os.path.join(COMFYUI_OUTPUT_DIR, f) for f in mp4_files], key=os.path.getctime)
    with open(latest_file, "rb") as vid_file:
        encoded_string = base64.b64encode(vid_file.read()).decode('utf-8')
    return encoded_string

def handler(job):
    job_input = job.get("input", {})
    
    try:
        # AŞAMA 1: Modellerin Kontrolü ve İndirilmesi
        yield {"status": "progress", "message": "Sistem: İsviçre Çakısı aktif. Yapay zeka modelleri kontrol ediliyor..."}
        
        dynamic_models = job_input.get("models_to_download", {})
        was_downloaded, msg = download_models_if_missing(dynamic_models)
        
        if was_downloaded:
            yield {"status": "progress", "message": "Sistem: İLK KURULUM veya YENİ MODEL - Modeller indiriliyor. Bu işlem boyutuna göre sürebilir..."}
        yield {"status": "progress", "message": msg}

        # JOKER MODU: Dışarıdan özel JSON ve Dosyalar gelmiş mi?
        workflow_json = job_input.get("workflow_json")
        if workflow_json:
            yield {"status": "progress", "message": "JOKER MODU: Özel JSON haritası algılandı. Blender es geçiliyor..."}
            
            # Gelen MP4/PNG dosyalarını ComfyUI Input klasörüne kaydet
            input_files = job_input.get("files", {})
            for filename, b64_data in input_files.items():
                filepath = os.path.join(COMFYUI_INPUT_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                yield {"status": "progress", "message": f"Dosya kaydedildi: {filename}"}
                
            yield {"status": "progress", "message": "Sistem: Joker JSON haritası ComfyUI'a gönderildi. Render başlıyor..."}
            final_video_base64 = run_comfyui_workflow(workflow_json)
            
        else:
            # KLASİK MOD: FBX'ten Video Üretimi
            fbx_base64 = job_input.get("fbx_base64")
            prompt_text = job_input.get("prompt", "a character dancing")
            
            if not fbx_base64:
                yield {"status": "error", "message": "FBX verisi VEYA workflow_json bulunamadı!"}
                return
                
            yield {"status": "progress", "message": "Sistem: Klasik Mod. Blender 3D kameraman devrede..."}
            temp_fbx = "/tmp/input_model.fbx"
            with open(temp_fbx, "wb") as f:
                f.write(base64.b64decode(fbx_base64))
                
            depth_video_path = generate_depth_map(temp_fbx)
            
            yield {"status": "progress", "message": "Sistem: Blender bitti! ComfyUI (ControlNet + AnimateDiff) video render işlemine başladı..."}
            # Lokal JSON dosyasını oku
            local_json_path = os.path.join(os.path.dirname(__file__), "workflow_api.json")
            with open(local_json_path, "r", encoding="utf-8") as f:
                workflow_json = json.load(f)
            # workflow_json dinamik değişiklikleri burada yapılabilir
            final_video_base64 = run_comfyui_workflow(workflow_json)

        return {
            "status": "success",
            "message": "Sistem: İşlem başarıyla tamamlandı!",
            "video_base64": final_video_base64
        }
        
    except Exception as e:
        yield {"status": "error", "message": str(e)}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
