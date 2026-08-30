# AI Creative Generator - Proje Yol Haritası

## 📚 Aşama 0: RunPod Öğrenme Eğrisi (Kritik Ön Hazırlık)
Bu projeyi başarılı bir şekilde RunPod'a taşıyabilmeniz için öncelikle RunPod'un şu özelliklerini öğrenmeniz/kavramanız gerekir:
- [ ] **Pods vs Serverless Ayrımı:** Geliştirme (Ar-Ge) yaparken "GPU Pods" (Jupyter/SSH erişimli), sistemi API'ye döktüğünüzde ise "Serverless" kullanma mantığı.
- [ ] **Network Volumes (Ağ Depolama - ÇOK KRİTİK):** Stable Diffusion, ControlNet ve AnimateDiff modelleri onlarca GB yer kaplar. Serverless her çalıştığında bunları baştan indirmemek için "Network Volume" oluşturup, bu modelleri kalıcı diske kaydetme ve Serverless container'ına bağlama (mount) mantığı.
- [ ] **Asenkron İşlemler (Async Endpoints):** Video/AI üretimi 1-2 dakika sürebilir. İstemcinin (Unity) HTTP Timeout yememesi için RunPod'un Asenkron API yapısını (Job ID alıp durumu sorgulama veya Webhook ile sonucu dinleme) öğrenmek.
- [ ] **Cold Start (Soğuk Başlangıç):** Docker imajı çok büyük olacağı için ilk tetiklemede makinenin uyanması zaman alacaktır. "Keep-Alive" (Aktif tutma) ve imaj boyutu optimizasyonu konuları.
- [ ] **RunPod Base Image'ları:** Sadece Python değil, hem CUDA (GPU sürücüleri) hem Blender çalıştıracak kütüphaneleri (libgl1 vb.) barındıran doğru Docker base imajını seçmek.

## 🚀 Aşama 1: ComfyUI İş Akışının (Workflow) Hazırlanması (Local R&D)
- [ ] Lokal Kurulum: ComfyUI, AnimateDiff, IP-Adapter ve ControlNet kurulumlarının lokalde yapılması.
- [ ] Manuel Test: Sisteme manuel olarak örnek bir Depth, OpenPose videosu ve 2D Karakter PNG'si vererek çıktıların kalitesinin test edilmesi.
- [ ] API Export: Kalitesinden emin olunan iş akışının (workflow) "Save (API Format)" ile `workflow_api.json` olarak dışa aktarılması.

## 🎬 Aşama 2: Blender Headless Otomasyonu (Veri Çıkarımı)
- [ ] Blender Script İskeleti: `.fbx` veya `.gltf` dosyalarını komut satırından import edecek `blender_script.py` dosyasının oluşturulması.
- [ ] Kamera Otomasyonu: Yüklenen karakterin etrafında dönecek kamera animasyonu kodunun yazılması.
- [ ] Render Pass Ayarları: "Depth Map" ve "OpenPose" pass'lerinin ayarlanıp dışa aktarılmasının otomatize edilmesi.

## ⚙️ Aşama 3: RunPod API (Handler) Geliştirmesi
- [ ] Blender Entegrasyonu: `handler.py` içerisine, gelen 3D modeli alıp `blender_script.py`'i subprocess olarak çalıştıracak kodun eklenmesi.
- [ ] JSON Manipülasyonu: Blender çıktılarının ve PNG'nin, Aşama 1'deki `workflow_api.json` dosyasına dinamik olarak yerleştirilmesi.
- [ ] ComfyUI İletişimi: JSON payload'unu, arka planda çalışan ComfyUI servisine gönderecek fonksiyonun yazılması.

## 🐳 Aşama 4: Docker & RunPod Deployment
- [ ] Dockerfile Güncellemesi: Mevcut `Dockerfile` içerisine Blender, ComfyUI ve Python gereksinimlerinin eklenmesi.
- [ ] Deployment: Hazırlanan Docker imajının RunPod Serverless ortamına yüklenmesi.

## 🔗 Aşama 5: İstemci (Client) Entegrasyonu ve Canlı Test
- [ ] Güvenlik & Endpoint: RunPod API Key ve Endpoint URL ayarları.
- [ ] Client Script: Oyun motorundan `.fbx` modeli ve PNG'yi sunucuya POST edecek scriptin yazılması.
- [ ] Uçtan Uca Test: Sistemin baştan sona çalıştırılıp nihai AI videosunun test edilmesi.
