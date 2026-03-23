import { useState } from 'react'
import ImageUploader from './components/ImageUploader'
import ResultViewer from './components/ResultViewer'
import './App.css'

export interface ConversionParams {
  threshold: number
  turdsize: number
  alphamax: number
  opticurve: boolean
  invert: boolean
}

export interface TraceAnalysis {
  mode: 'auto' | 'manual'
  notes?: string[]
  stats?: {
    mean_brightness?: number
    background_level?: number
    dark_ratio?: number
    longest_edge?: number
  }
  strategy?: Record<string, string>
}

export interface ConversionResult {
  svg_content: string
  original_size: [number, number]
  processing_time: number
  parameters: ConversionParams
  auto_mode: boolean
  analysis?: TraceAnalysis | null
}

function App() {
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [result, setResult] = useState<ConversionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'fill' | 'stroke'>('stroke')
  const [strokeEngine, setStrokeEngine] = useState<'geometric' | 'organic'>('geometric')

  const handleConvert = async () => {
    if (!imageFile || loading) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', imageFile)
    formData.append('auto_mode', 'true')
    formData.append('mode', mode)
    if (mode === 'stroke') {
      formData.append('stroke_engine', strokeEngine)
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002'
      const response = await fetch(`${apiUrl}/convert`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Conversion failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setImageFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>PNG to Vector Converter</h1>
        <p>Convert your PNG images to editable SVG vectors for Figma</p>
      </header>

      <div className="app-content">
        <div className="left-panel">
          <ImageUploader
            onFileSelect={setImageFile}
            selectedFile={imageFile}
            disabled={loading}
          />

          <div className="action-card">
            <h3>Vectoriza en un clic</h3>
            <p className="action-subtitle">
              Nuestro motor analiza el logo, elige el umbral ideal y limpia el ruido automáticamente.
            </p>

            <div className="mode-selector">
              <label className="mode-option">
                <input
                  type="radio"
                  name="mode"
                  value="stroke"
                  checked={mode === 'stroke'}
                  onChange={() => setMode('stroke')}
                />
                <div className="mode-content">
                  <strong>Strokes editables</strong>
                  <span>Líneas con grosor ajustable en Figma</span>
                </div>
              </label>
              <label className="mode-option">
                <input
                  type="radio"
                  name="mode"
                  value="fill"
                  checked={mode === 'fill'}
                  onChange={() => setMode('fill')}
                />
                <div className="mode-content">
                  <strong>Formas rellenas</strong>
                  <span>Más precisión, pero no editable como stroke</span>
                </div>
              </label>
            </div>

            {mode === 'stroke' && (
              <div className="engine-selector">
                <p className="engine-label">Tipo de contenido:</p>
                <div className="engine-options">
                  <label className={`engine-option ${strokeEngine === 'geometric' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="engine"
                      value="geometric"
                      checked={strokeEngine === 'geometric'}
                      onChange={() => setStrokeEngine('geometric')}
                    />
                    <div className="engine-content">
                      <span className="engine-icon">📐</span>
                      <span className="engine-name">Geométrico</span>
                      <span className="engine-desc">Iconos, UI, líneas rectas</span>
                    </div>
                  </label>
                  <label className={`engine-option ${strokeEngine === 'organic' ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="engine"
                      value="organic"
                      checked={strokeEngine === 'organic'}
                      onChange={() => setStrokeEngine('organic')}
                    />
                    <div className="engine-content">
                      <span className="engine-icon">✏️</span>
                      <span className="engine-name">Orgánico</span>
                      <span className="engine-desc">Manuscrito, ilustraciones</span>
                    </div>
                  </label>
                </div>
              </div>
            )}

            <button
              className="primary-button"
              onClick={handleConvert}
              disabled={!imageFile || loading}
            >
              {loading ? 'Analizando...' : 'Convertir a SVG'}
            </button>
            <p className="microcopy">
              Sube un PNG y presiona convertir. Sin sliders. Sin configuraciones raras.
            </p>
            {(imageFile || result) && (
              <button className="secondary-button" onClick={handleReset} disabled={loading}>
                Empezar de nuevo
              </button>
            )}
          </div>
        </div>

        <div className="right-panel">
          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {loading && (
            <div className="loading-message">
              <div className="spinner"></div>
              <p>Converting image to vector...</p>
            </div>
          )}

          {result && !loading && (
            <ResultViewer result={result} originalFile={imageFile} />
          )}

          {!imageFile && !loading && !error && (
            <div className="placeholder">
              <svg
                width="120"
                height="120"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
              <p>Sube un PNG y deja que hagamos la magia</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
