#!/usr/bin/env python3
import json
from pathlib import Path

def restart_images_phase(slug):
    project_file = Path(f'C:/videomaker/projects/{slug}/project.json')
    
    with open(project_file, 'r', encoding='utf-8') as f:
        project_data = json.load(f)
    
    # Reset images phase to pending
    project_data['phases']['images'] = {
        'done': False,
        'ts': None,
        'detail': None
    }
    
    # Add to history
    project_data['history'].append({
        'ts': '2026-11-13 20:05:41',
        'phase': 'images',
        'event': 'reiniciado',
        'detail': 'Reiniciado para nova geracao'
    })
    
    # Write back
    with open(project_file, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=2)
    
    print(f'PIPELINE REINICIADO para fase images (slug: {slug})')
    print('E necessario executar scripts/pipeline.py full para continuar a geracao.')

if __name__ == '__main__':
    restart_images_phase("o-co-de-frias")