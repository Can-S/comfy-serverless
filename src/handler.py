import runpod
import json
import os
import subprocess
import base64
import urllib.request
import time
import socket
import sys
import glob

# --- AYARLAR ---
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_OUTPUT_DIR = "/comfyui/output"
COMFYUI_INPUT_DIR = "/comfyui/input"
WORKFLOW_PATH = "/workflow.json"

# --- ComfyUI'ı Başlat ---
def start_comfyui():
    """ComfyUI sunucusunu arka planda başlatır ve hazır olmasını bekler."""
    print("Sistem: ComfyUI sunucusu başlatılıyor...")
    subprocess.Popen(
        [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd="/comfyui",
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    # Port 8188 açılana kadar bekle (maks 120 saniye)
    for i in range(120):
        try:
            with socket.create_connection(("127.0.0.1", 8188), timeout=1):
                print(f"Sistem: ComfyUI sunucusu {i+1} saniyede hazır oldu!")
                return True
        except OSError:
            time.sleep(1)
    print("HATA: ComfyUI sunucusu 120 saniye içinde başlatılamadı!")
    return False

# Sunucu başlat (worker ilk yüklendiğinde bir kere çalışır)
comfyui_ready = start_comfyui()

# İmajın içine gömülü workflow JSON'ı bir kere oku
with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
    WORKFLOW_JSON = json.load(f)
print(f"Sistem: Workflow JSON yüklendi ({len(WORKFLOW_JSON)} node)")


def handler(job):
    """
    API'den sadece video ve resim dosyaları alır.
    Workflow JSON zaten imajın içinde gömülü.
    """
    job_input = job.get("input", {})
    
    if not comfyui_ready:
        return {"status": "error", "message": "ComfyUI sunucusu başlatılamadı!"}
    
    try:
        # AŞAMA 1: Gelen dosyaları ComfyUI input klasörüne kaydet
        # Format: "images": [{"name": "dosya.mp4", "image": "base64..."}]
        images = job_input.get("images", [])
        if not images:
            return {"status": "error", "message": "Dosya bulunamadı! 'images' listesi boş."}
        
        video_filename = None
        image_filename = None
        
        for img_info in images:
            filename = img_info.get("name", "input.png")
            b64_data = img_info.get("image", "")
            
            # "data:image/png;base64," prefix varsa temizle
            if "base64," in b64_data:
                b64_data = b64_data.split("base64,")[1]
            
            filepath = os.path.join(COMFYUI_INPUT_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_data))
            print(f"Dosya kaydedildi: {filename}")
            
            # Dosya tipini belirle
            if filename.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                video_filename = filename
            else:
                image_filename = filename
        
        # AŞAMA 2: Workflow JSON'daki input node'larını güncelle
        workflow = json.loads(json.dumps(WORKFLOW_JSON))  # Derin kopya
        
        if video_filename and "155" in workflow:
            workflow["155"]["inputs"]["file"] = video_filename
            print(f"Workflow güncellendi: LoadVideo -> {video_filename}")
        
        if image_filename and "30" in workflow:
            workflow["30"]["inputs"]["image"] = image_filename
            print(f"Workflow güncellendi: LoadImage -> {image_filename}")
        
        # Prompt metni geldiyse her iki subgraph'a da enjekte et
        prompt_text = job_input.get("prompt")
        if prompt_text:
            # Base subgraph (node 213:3)
            if "213:3" in workflow:
                workflow["213:3"]["inputs"]["text"] = prompt_text
            # Extend subgraph (node 262:258)
            if "262:258" in workflow:
                workflow["262:258"]["inputs"]["text"] = prompt_text
            print(f"Workflow güncellendi: Prompt -> {prompt_text[:60]}...")
        
        # Output klasörünü temizle (önceki çalışmalardan kalan dosyalar karışmasın)
        video_dir = os.path.join(COMFYUI_OUTPUT_DIR, "video")
        os.makedirs(video_dir, exist_ok=True)
        
        data = json.dumps({"prompt": workflow}).encode('utf-8')
        req = urllib.request.Request(COMFYUI_API_URL, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            prompt_id = result.get("prompt_id")
        
        print(f"ComfyUI iş kuyruğuna eklendi. Prompt ID: {prompt_id}")
        
        # AŞAMA 3: İşlem bitene kadar bekle
        timeout = 1800  # 30 dakika (SCAIL-2 uzun sürebilir)
        start = time.time()
        
        while time.time() - start < timeout:
            req_hist = urllib.request.Request(f"http://127.0.0.1:8188/history/{prompt_id}")
            with urllib.request.urlopen(req_hist) as hist_res:
                history = json.loads(hist_res.read())
                if prompt_id in history:
                    prompt_result = history[prompt_id]
                    if prompt_result.get("status", {}).get("completed", False):
                        print("ComfyUI render tamamlandı!")
                        break
                    if prompt_result.get("status", {}).get("status_str") == "error":
                        error_msg = str(prompt_result.get("status", {}))
                        return {"status": "error", "message": f"ComfyUI hatası: {error_msg}"}
            time.sleep(3)
        else:
            return {"status": "error", "message": "Zaman aşımı! 30 dakika içinde tamamlanamadı."}
        
        # AŞAMA 4: Çıktı dosyalarını bul ve base64 olarak döndür
        result_images = []
        
        # Tüm çıktı dosyalarını bul (video ve resim)
        for root, dirs, files in os.walk(COMFYUI_OUTPUT_DIR):
            for filename in sorted(files):
                if filename.endswith(('.mp4', '.png', '.jpg', '.webp', '.gif')):
                    filepath = os.path.join(root, filename)
                    with open(filepath, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode('utf-8')
                    result_images.append({
                        "name": filename,
                        "image": encoded,
                        "type": "base64"
                    })
                    print(f"Çıktı dosyası eklendi: {filename}")
        
        if not result_images:
            return {"status": "error", "message": "ComfyUI hiç çıktı dosyası üretmedi!"}
        
        return {
            "status": "success",
            "message": f"İşlem tamamlandı! {len(result_images)} dosya üretildi.",
            "images": result_images
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
