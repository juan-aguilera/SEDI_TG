# SEDI_TG
Repositorio creado para llevar trazabilidad del progreso del trabajo de grado, tener a la mano archivos importantes (Ej: Papers, Datasets, etc) y generar un espacio colaborativo con mi director de trabajo de grado. 

## ¿Cómo acceder al dump file?

El dump está disponible públicamente a través de Hugging Face Datasets.
Puedes descargarlo o clonarlo libremente, pero solo el autor tiene permisos para subir nuevas versiones.

## Opción 1: Descargarlo directamente desde Hugging Face

Puedes acceder y descargar los archivos desde la página oficial:

🔗 https://huggingface.co/datasets/Juanes-Aguilera/HuggingFace-Dump-File

## Opción 2: Clonar el repositorio del dataset (solo lectura)

Ejecuta en tu terminal:

git clone https://huggingface.co/datasets/Juanes-Aguilera/HuggingFace-Dump-File
cd HuggingFace-Dump-File


Esto descargará todos los archivos localmente.
## Importante: este repositorio solo permite lectura (descarga).
No podrás subir cambios (git push) a menos que tengas permisos de colaborador.

## Notas técnicas

El dataset usa Git LFS (Large File Storage) para archivos grandes (>5 GB).
Si lo clonas manualmente y deseas gestionar archivos grandes localmente, asegúrate de tener instalado:
git lfs install
