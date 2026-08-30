import bpy
import sys
import os

# KULLANIM: 
# Bu script arka planda (headless) şu komutla çalıştırılır:
# blender -b -P blender_extract.py -- <fbx_dosyasi_yolu> <cikti_klasoru>

def clear_scene():
    """Sahnedeki varsayılan küp, kamera ve ışıkları temizler."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_depth_rendering(output_path):
    """ComfyUI ControlNet'i için Z-Depth (Derinlik) haritası render ayarlarını yapar."""
    scene = bpy.context.scene
    
    # Render motoru ayarları
    scene.render.engine = 'CYCLES' # Depth kalitesi için veya EEVEE
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'BW' # Siyah Beyaz
    
    # Compositor (Düğüm) ayarları: Z-Depth'i normalize edip çıktıya bağlarız
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    
    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    normalize = tree.nodes.new(type="CompositorNodeNormalize")
    file_output = tree.nodes.new(type="CompositorNodeOutputFile")
    
    file_output.base_path = output_path
    file_output.format.file_format = 'PNG'
    
    # Düğümleri birbirine bağlıyoruz (Z değerini normalize edip dosyaya yaz)
    tree.links.new(render_layers.outputs['Depth'], normalize.inputs[0])
    tree.links.new(normalize.outputs[0], file_output.inputs[0])

def main():
    # Komut satırından gelen argümanları al
    # Blender özel argümanları '--' işaretinden sonrasını alır
    argv = sys.argv
    if "--" not in argv:
        print("Hata: Argümanlar eksik. (Kullanım: blender -b -P script.py -- <fbx> <out>)")
        return
        
    args = argv[argv.index("--") + 1:]
    if len(args) < 2:
        print("Hata: FBX yolu veya Çıktı klasörü belirtilmedi.")
        return
        
    fbx_path = args[0]
    output_dir = args[1]
    
    print(f"[*] Temizlik yapılıyor...")
    clear_scene()
    
    print(f"[*] FBX İçe Aktarılıyor: {fbx_path}")
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    
    # TODO: İleride buraya otomatik kamera yerleştirme ve animasyon oynatma kodları eklenecek
    
    print(f"[*] Render Ayarları Yapılıyor...")
    setup_depth_rendering(output_dir)
    
    print(f"[+] Hazırlık Tamam! API entegrasyonu için script iskeleti oluşturuldu.")

if __name__ == "__main__":
    main()
