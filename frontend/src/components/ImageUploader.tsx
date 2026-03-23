import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import './ImageUploader.css'

interface ImageUploaderProps {
  onFileSelect: (file: File | null) => void
  selectedFile: File | null
  disabled?: boolean
}

export default function ImageUploader({ onFileSelect, selectedFile, disabled }: ImageUploaderProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/gif': ['.gif'],
      'image/bmp': ['.bmp']
    },
    maxFiles: 1,
    disabled
  })

  return (
    <div className="image-uploader">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
      >
        <input {...getInputProps()} />

        {selectedFile ? (
          <div className="file-preview">
            <img
              src={URL.createObjectURL(selectedFile)}
              alt="Preview"
              className="preview-image"
            />
            <div className="file-info">
              <p className="filename">{selectedFile.name}</p>
              <p className="filesize">{(selectedFile.size / 1024).toFixed(2)} KB</p>
            </div>
          </div>
        ) : (
          <div className="upload-prompt">
            <svg
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p className="main-text">
              {isDragActive ? 'Drop your image here' : 'Drag & drop an image'}
            </p>
            <p className="sub-text">or click to browse</p>
            <p className="format-text">PNG, JPG, GIF, BMP supported</p>
          </div>
        )}
      </div>

      {selectedFile && !disabled && (
        <button
          className="clear-button"
          onClick={(e) => {
            e.stopPropagation()
            onFileSelect(null)
          }}
        >
          Clear Image
        </button>
      )}
    </div>
  )
}
