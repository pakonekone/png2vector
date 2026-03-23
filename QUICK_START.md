# Quick Start Guide

## Instalación rápida (5 minutos)

### 1. Instalar potrace (requerido)

**macOS:**
```bash
brew install potrace
```

**Ubuntu/Debian:**
```bash
sudo apt-get install potrace
```

**Windows:**
Descarga desde http://potrace.sourceforge.net/

### 2. Instalar dependencias del proyecto

```bash
# En la raíz del proyecto
npm install

# Instalar backend
cd backend
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Instalar frontend
cd frontend
npm install
cd ..
```

### 3. Iniciar la aplicación

```bash
# Desde la raíz del proyecto (inicia backend + frontend)
npm run dev
```

O iniciar por separado:

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 4. Usar la aplicación

1. Abre http://localhost:5173 en tu navegador.
2. Arrastra una imagen PNG (o usa clic para seleccionar).
3. Presiona “Convertir a SVG”. La app analiza el logo/icono y escoge automáticamente el umbral, limpieza de ruido e inversión de color.
4. Descarga el SVG listo para Figma.

## Solución de problemas

### Error: "potrace not found"
Asegúrate de instalar potrace con brew/apt-get

### Error en importación de pypotrace
```bash
cd backend
source venv/bin/activate
pip install --force-reinstall pypotrace
```

### Puerto 8000 o 5173 ya en uso
```bash
# Cambiar puerto del backend en package.json
"dev:backend": "cd backend && uvicorn main:app --reload --port 8001"

# Cambiar puerto del frontend en frontend/vite.config.ts
server: { port: 5174 }
```

## Mejores prácticas

- Logos de alto contraste funcionan mejor (fondos claros con trazos oscuros).
- Si tu imagen tiene fondo transparente, no pasa nada: el backend lo detecta y mantiene el contraste.
- Para ilustraciones complejas, exporta una versión simplificada (menos ruido) antes de convertir.

## API Usage

Si quieres usar solo el backend:

```bash
curl -X POST "http://localhost:8000/convert" \
  -F "file=@/path/to/image.png" \
  -F "auto_mode=true"
```

Respuesta:
```json
{
  "svg_content": "<svg>...</svg>",
  "original_size": [800, 600],
  "processing_time": 0.15,
  "parameters": {...},
  "auto_mode": true,
  "analysis": {...}
}
```
