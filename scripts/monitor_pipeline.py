import time
from pathlib import Path
import subprocess

def check_pipeline_status(slug):
    try:
        result = subprocess.run(
            ['C:/OpenMontage\.venv/Scripts/python.exe', 'scripts/pipeline.py', 'status', '--slug', slug],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout
    except Exception as e:
        return f"Erro: {e}"

def monitor_pipeline(slug, max_wait_minutes=60):
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    print(f"=== Monitorando pipeline para projeto: {slug} ===")
    print(f"Tempo limite: {max_wait_minutes} minutos")
    print()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print("Tempo limite atingido!")
            break
            
        status_output = check_pipeline_status(slug)
        
        # Parse status
        images_status = None
        render_status = None
        
        for line in status_output.split('\n'):
            if line.strip().startswith('images'):
                images_status = line.strip()
            elif line.strip().startswith('render'):
                render_status = line.strip()
        
        print(f"[{time.strftime('%H:%M:%S')}] Status:")
        if images_status:
            print(f"  {images_status}")
        if render_status:
            print(f"  {render_status}")
        
        # Check if pipeline is complete
        if images_status and "OK" in images_status and render_status and "OK" in render_status:
            print(f"\n✅ PIPELINE CONCLUÍDO após {elapsed/60:.1f} minutos!")
            break
        
        # Check image count
        try:
            images_path = Path(f'C:/videomaker/projects/{slug}/assets/images/gemini/scenes')
            if images_path.exists():
                image_files = list(images_path.glob('*.jpg'))
                print(f"  📸 Imagens geradas: {len(image_files)} de 28 esperadas")
                if len(image_files) >= 28:
                    print(f"  📋 Todas as imagens foram geradas!")
        except Exception as e:
            print(f"  ⚠️  Erro ao contar imagens: {e}")
        
        print(f"  ⏳ Aguardando... ({elapsed/60:.1f} min)")
        print()
        
        time.sleep(30)  # Verifica a cada 30 segundos

if __name__ == "__main__":
    monitor_pipeline("o-co-de-frias", max_wait_minutes=120)