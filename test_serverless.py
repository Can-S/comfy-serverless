import requests
import json
import time
import base64

# --- AYARLAR (BURAYI KENDİNİZE GÖRE DOLDURUN) ---
API_KEY = "RUNPOD_API_ANAHTARINIZI_BURAYA_YAZIN"
ENDPOINT_ID = "RUNPOD_ENDPOINT_ID_BURAYA"
# -----------------------------------------------

RUN_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def file_to_b64(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

print("=" * 60)
print("🚀 SCAIL-2 Serverless API Testi")
print("   Workflow JSON imajın içinde gömülü.")
print("   Sadece video ve resim gönderiliyor!")
print("=" * 60)

# Sadece dosyaları ve promptu gönder — workflow zaten sunucuda
payload = {
    "input": {
        "prompt": "A young woman with dark hair tied in a neat high bun, with a few loose strands framing her face, is dancing outdoors on a sunny coastal hillside. She has a normal-sized head and a slim face, with no hat, no headwear, and no oversized hair volume. She wears a fitted black long-sleeve crop top with a shoulder cutout, extremely baggy black cargo pants with straps and pockets, and chunky black combat boots. She performs energetic dance moves with one leg lifted and arms extended, moving naturally in front of a large tree, a small white stone house with a terracotta roof, and a bright blue sea under a clear sky with light clouds.",
        "images": [
            {
                "name": "driving_outdoor_dance.mp4",
                "image": file_to_b64("test/driving_outdoor_dance.mp4")
            },
            {
                "name": "reference_streetwear_character.png",
                "image": file_to_b64("test/view.jpg")
            }
        ]
    }
}

print(f"📦 Payload boyutu: {len(json.dumps(payload)) / 1024 / 1024:.1f} MB")
print("📡 RunPod'a gönderiliyor...")

# İsteği Gönder
try:
    response = requests.post(RUN_URL, json=payload, headers=headers, timeout=30)
    response_data = response.json()
    job_id = response_data.get("id")
    
    if not job_id:
        print(f"❌ HATA: {response_data}")
        exit()
        
    print(f"✅ Job ID: {job_id}")
    print("-" * 60)
    
except Exception as e:
    print(f"❌ Bağlantı Hatası: {e}")
    exit()

# Sonucu Bekle
status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
start_time = time.time()

while True:
    try:
        status_res = requests.get(status_url, headers=headers).json()
        status = status_res.get("status")
        elapsed = int(time.time() - start_time)
        
        if status == "COMPLETED":
            print(f"\n🎉 İŞLEM BİTTİ! ({elapsed} saniye)")
            
            output = status_res.get("output", {})
            
            if isinstance(output, dict) and output.get("status") == "success":
                images = output.get("images", [])
                for i, img in enumerate(images):
                    name = img.get("name", f"sonuc_{i}")
                    decoded = base64.b64decode(img["image"])
                    with open(name, "wb") as f:
                        f.write(decoded)
                    print(f"✅ Kaydedildi: {name} ({len(decoded)/1024:.0f} KB)")
            else:
                print(f"Çıktı: {output}")
            break
            
        elif status == "FAILED":
            print(f"\n❌ HATA: {status_res.get('error', status_res)}")
            break
            
        else:
            print(f"⏳ [{elapsed}s] {status}")
            time.sleep(10)
        
    except Exception as e:
        print(f"⚠️  Hata: {e}")
        time.sleep(10)
