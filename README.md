# PNG to Vector (SVG) Converter

Herramienta web para convertir imágenes PNG a SVG vectoriales 100% editables en Figma.

## Características

- ✨ Trazado vectorial real usando potrace (no simple wrapper)
- 🎨 100% editable en Figma (paths vectoriales puros)
- 🖱️ Interfaz drag & drop intuitiva
- 👁️ Preview en tiempo real del resultado
- 🧠 Ajustes automáticos optimizados para logos e iconos (umbral, suavizado, inversión)
- 📦 Sin dependencias externas complejas

## Instalación

### Requisitos previos
- Python 3.9+
- Node.js 18+
- potrace (instalación según sistema operativo)

### macOS
```bash
brew install potrace
```

### Ubuntu/Debian
```bash
sudo apt-get install potrace
```

### Instalación del proyecto
```bash
# Instalar dependencias
npm run install-all
```

## Uso

### Iniciar el servidor completo
```bash
npm run dev
```

Esto iniciará:
- Backend en http://localhost:8000
- Frontend en http://localhost:5173

### Uso manual

#### Backend solo
```bash
cd backend
uvicorn main:app --reload --port 8000
```

#### Frontend solo
```bash
cd frontend
npm run dev
```

## API Endpoints

### POST /convert
Convierte PNG a SVG con trazado vectorial.

**Body (multipart/form-data)**:
- `file` (requerido): archivo PNG/JPG/etc.
- `auto_mode` (opcional, default `true`): cuando es `true`, el backend calcula automáticamente `threshold`, `turdsize`, `alphamax`, `invert` y `opticurve`.
- `threshold`, `turdsize`, `alphamax`, `invert`, `opticurve` (opcionales): solo se usan cuando `auto_mode=false`, para quienes necesiten ajustes avanzados vía API.

**Response**:
```json
{
  "svg_content": "<svg>...</svg>",
  "original_size": [800, 600],
  "processing_time": 0.15,
  "parameters": {
    "threshold": 147,
    "turdsize": 2,
    "alphamax": 1.0,
    "opticurve": true,
    "invert": true
  },
  "auto_mode": true,
  "analysis": {
    "mode": "auto",
    "notes": [
      "Detected light background",
      "Auto threshold locked at 147 for maximum contrast."
    ]
  }
}
```

## Cómo funciona

1. **Upload**: Subes tu imagen PNG
2. **Conversión a escala de grises**: Se convierte la imagen a blanco y negro
3. **Binarización**: Aplica umbral para crear imagen binaria
4. **Trazado vectorial**: potrace genera paths vectoriales siguiendo contornos
5. **Generación SVG**: Crea SVG con paths editables en Figma

## Modo automático

Cada conversión analiza la imagen y:
- Calcula el umbral ideal con Otsu para maximizar el contraste.
- Detecta si el fondo es claro u oscuro para decidir si invierte colores antes de vectorizar.
- Ajusta el suavizado y la limpieza de ruido según el tamaño y densidad del trazo.

Si aún así necesitas control manual, puedes desactivar `auto_mode` desde la API y enviar tus propios parámetros.

## Mejores prácticas

- Logos e iconos planos funcionan mejor
- Imágenes con alto contraste dan mejores resultados
- Para ilustraciones muy complejas, considera simplificarlas antes de vectorizar

## Limitaciones

- No preserva colores (convierte a monocromo)
- Imágenes muy complejas pueden generar SVG pesados
- Fotos realistas no son ideales para vectorización

## Desarrollo

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Licencia

MIT
