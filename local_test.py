import src.handler as runpod_worker

# RunPod'un sunucudan göndereceği "Job" (İş) paketini lokalde simüle ediyoruz
mock_job = {
    "id": "local_test_12345",
    "input": {
        "name": "Can (Lokal Test)"
    }
}

print("Lokal test başlatılıyor...\n")

# Handler fonksiyonumuzu doğrudan çalıştırıyoruz
sonuc = runpod_worker.handler(mock_job)

print("RunPod'un kullanıcıya döneceği sonuç:")
print(sonuc)
