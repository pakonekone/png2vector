# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PNG to Vector Converter: a web tool that converts PNG/JPG/GIF/BMP images to SVG vectors editable in Figma. Uses potrace (filled shapes) and autotrace (editable strokes) for real vectorization—not simple image embedding.

## Commands

```bash
# Start both backend and frontend (dev mode)
npm run dev

# Install all dependencies (backend venv + frontend npm)
npm run install-all

# Backend only
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# Frontend only
cd frontend && npm run dev

# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Build frontend for production
cd frontend && npm run build
```

## System Requirements

- Python 3.9+
- Node.js 18+
- **potrace** (`brew install potrace` on macOS, `apt-get install potrace` on Ubuntu)
- **autotrace** (for stroke/centerline mode)

## Architecture

### Backend (FastAPI - `backend/main.py`)

Single-file API with two vectorization modes:

1. **Fill mode** (potrace): `image_to_svg()` - generates filled shapes via potrace CLI
2. **Stroke mode** (autotrace): `image_to_svg_centerline()` - generates editable strokes via autotrace CLI

Key function: `auto_trace_parameters()` uses Otsu thresholding to automatically determine optimal threshold, invert decision (based on border sampling), and smoothing parameters.

Conversion pipeline:
1. Flatten transparency over white background
2. Convert to grayscale
3. Apply binary threshold
4. Save as BMP (required by potrace/autotrace)
5. Run CLI tool
6. Return SVG content

**Endpoints:**
- `POST /convert` - Main conversion (multipart/form-data with `file`, `mode`, `auto_mode`, `quality_mode`)
- `GET /health` - Check potrace availability
- `GET /` - Health check

### Frontend (React + Vite + TypeScript - `frontend/src/`)

- `App.tsx` - Main state management, mode selector (fill/stroke), conversion trigger
- `components/ImageUploader.tsx` - Drag-and-drop with react-dropzone
- `components/ResultViewer.tsx` - SVG preview, download, copy code, analysis display

The frontend hits `http://localhost:8000/convert` directly (CORS configured for ports 5173, 5174, 3000).

## API Response Shape

```typescript
interface ConversionResult {
  svg_content: string
  original_size: [number, number]
  processing_time: number
  parameters: {
    threshold: number
    turdsize: number
    alphamax: number
    opticurve: boolean
    invert: boolean
    mode?: 'fill' | 'stroke'
    quality_mode?: 'fast' | 'balanced' | 'maximum'
  }
  auto_mode: boolean
  analysis: {
    mode: 'auto' | 'manual'
    notes: string[]
    stats?: { mean_brightness, background_level, dark_ratio, longest_edge }
    strategy?: { threshold, invert_reason, smoothing_reason, speckle_reason }
  }
}
```

## Key Implementation Details

- Transparent PNGs are composited over white before processing
- Invert is determined by sampling border pixels: dark backgrounds (< 110 brightness) with >50% dark pixels trigger inversion
- Stroke mode has three quality profiles: `fast`, `balanced`, `maximum` with different error-threshold and filter-iterations
- No upscaling in centerline mode to avoid waviness artifacts
