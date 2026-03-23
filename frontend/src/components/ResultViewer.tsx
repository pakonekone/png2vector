import { useState } from 'react'
import { ConversionResult } from '../App'
import './ResultViewer.css'

interface ResultViewerProps {
  result: ConversionResult
  originalFile: File | null
}

export default function ResultViewer({ result, originalFile }: ResultViewerProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview')
  const analysis = result.analysis || undefined

  const downloadSVG = () => {
    const blob = new Blob([result.svg_content], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = originalFile
      ? originalFile.name.replace(/\.[^/.]+$/, '.svg')
      : 'converted.svg'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const copySVGCode = async () => {
    try {
      await navigator.clipboard.writeText(result.svg_content)
      alert('SVG code copied to clipboard!')
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const svgDataUrl = `data:image/svg+xml;base64,${btoa(result.svg_content)}`

  return (
    <div className="result-viewer">
      <div className="result-header">
        <h3>Conversion Result</h3>
        <div className="stats">
          <span className="stat">
            {result.original_size[0]} × {result.original_size[1]}px
          </span>
          <span className="stat">
            {result.processing_time}s
          </span>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          Preview
        </button>
        <button
          className={`tab ${activeTab === 'code' ? 'active' : ''}`}
          onClick={() => setActiveTab('code')}
        >
          SVG Code
        </button>
      </div>

      <div className="result-content">
        {activeTab === 'preview' ? (
          <div className="preview-container">
            <div className="preview-grid">
              <img
                src={svgDataUrl}
                alt="SVG Result"
                className="svg-preview"
              />
            </div>
            <div className="preview-info">
              <p>This SVG is fully editable in Figma</p>
              <p className="small">All shapes are vector paths</p>
            </div>
          </div>
        ) : (
          <div className="code-container">
            <pre>
              <code>{result.svg_content}</code>
            </pre>
          </div>
        )}
      </div>

      <div className="result-actions">
        <button className="download-button" onClick={downloadSVG}>
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download SVG
        </button>

        <button className="copy-button" onClick={copySVGCode}>
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          Copy Code
        </button>
      </div>

      {analysis && (
        <div className="analysis-card">
          <div className="analysis-header">
            <h4>Ajustes inteligentes</h4>
            <span className="pill">{result.auto_mode ? 'Auto' : 'Manual'}</span>
          </div>
          <div className="analysis-grid">
            <div className="analysis-metric">
              <span className="metric-label">Fondo</span>
              <strong>{Math.round(analysis.stats?.background_level ?? 0)}</strong>
              <small>/255</small>
            </div>
            <div className="analysis-metric">
              <span className="metric-label">Contraste</span>
              <strong>{Math.round((analysis.stats?.dark_ratio ?? 0) * 100)}%</strong>
              <small>pixeles oscuros</small>
            </div>
            <div className="analysis-metric">
              <span className="metric-label">Edge más largo</span>
              <strong>{analysis.stats?.longest_edge ?? '—'}</strong>
              <small>px</small>
            </div>
          </div>
          {analysis.notes && (
            <ul className="analysis-notes">
              {analysis.notes.map((note, index) => (
                <li key={`${note}-${index}`}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="conversion-params">
        <h4>Settings Used</h4>
        <div className="params-grid">
          <div className="param">
            <span className="param-label">Threshold:</span>
            <span className="param-value">{result.parameters.threshold}</span>
          </div>
          <div className="param">
            <span className="param-label">Despeckle:</span>
            <span className="param-value">{result.parameters.turdsize}</span>
          </div>
          <div className="param">
            <span className="param-label">Smoothing:</span>
            <span className="param-value">{result.parameters.alphamax.toFixed(2)}</span>
          </div>
          <div className="param">
            <span className="param-label">Inverted:</span>
            <span className="param-value">{result.parameters.invert ? 'Yes' : 'No'}</span>
          </div>
          <div className="param">
            <span className="param-label">Optimize:</span>
            <span className="param-value">{result.parameters.opticurve ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
