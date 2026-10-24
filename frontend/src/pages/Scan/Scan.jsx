import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Camera,
  CheckCircle2,
  FileImage,
  Info,
  RefreshCw,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import { scanService } from '../../services/scanService.js';
import './Scan.css';

const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB per backend
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'];

export function Scan() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [apiError, setApiError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(''); // 'uploading' | 'predicting' | 'completed'

  // Clean up object URL memory leak on unmount or file change
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const validateAndSelectFile = (file) => {
    setValidationError('');
    setApiError('');

    if (!file) return;

    // 1. Check type
    const fileType = file.type.toLowerCase();
    const isValidType =
      ALLOWED_TYPES.includes(fileType) ||
      /\.(jpe?g|png|webp|heic)$/i.test(file.name);

    if (!isValidType) {
      setValidationError('Please select a valid image file (JPEG, PNG, or WebP).');
      return;
    }

    // 2. Check size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError('The image file is too large. Maximum size allowed is 20 MB.');
      return;
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    const objectUrl = URL.createObjectURL(file);
    setSelectedFile(file);
    setPreviewUrl(objectUrl);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    validateAndSelectFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    validateAndSelectFile(file);
  };

  const handleClear = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setValidationError('');
    setApiError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const handleStartDiagnosis = async () => {
    if (!selectedFile) {
      setValidationError('Please select or capture a Tur leaf image first.');
      return;
    }

    setIsProcessing(true);
    setApiError('');
    setValidationError('');

    try {
      // Step 1: Upload image to create scan record
      setCurrentStep('uploading');
      const uploadResult = await scanService.uploadScan(selectedFile, selectedFile.name);
      const scanId = uploadResult?.scan_id;

      if (!scanId) {
        throw new Error('Scan upload did not return a valid scan identifier.');
      }

      // Step 2: Trigger ML leaf prediction on stored scan
      setCurrentStep('predicting');
      const predictionResult = await scanService.runPrediction(scanId);

      // Step 3: Successfully completed — navigate to results
      setCurrentStep('completed');
      navigate(`/result/${scanId}`, {
        state: {
          scan: predictionResult,
          imagePreview: previewUrl,
        },
      });
    } catch (err) {
      setIsProcessing(false);
      setCurrentStep('');

      if (err.status === 422) {
        // Gate rejection, non-tur crop or low confidence
        setApiError(
          err.detail ||
            'The uploaded image was rejected by our quality gate. Please ensure the leaf is clearly visible and belongs to a Tur crop.'
        );
      } else if (err.status === 503) {
        setApiError(
          'The AI prediction model is temporarily updating or offline. Your scan record has been safely saved.'
        );
      } else {
        setApiError(
          err.detail ||
            err.message ||
            'Unable to process the image. Please verify backend connection and try again.'
        );
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  return (
    <div className="scan-page-layout">
      <Navbar />

      <main className="scan-main-content">
        <div className="scan-header-card">
          <h1>Scan Tur Crop Leaf</h1>
          <p>
            Upload a high-resolution photograph of the affected Tur (Pigeonpea) leaf for instant disease identification.
          </p>
        </div>

        {/* Diagnostic workspace */}
        <div className="scan-workspace">
          {!previewUrl ? (
            /* Upload dropzone when no file selected */
            <div
              className={`upload-dropzone ${isDragging ? 'is-dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="dropzone-icon-circle">
                <Upload size={36} />
              </div>

              <h3>Upload or Drag & Drop Tur Leaf Image</h3>
              <p className="dropzone-hint">
                Supports JPG, PNG, WebP up to 20 MB. Ensure natural daylight and sharp focus.
              </p>

              <div className="dropzone-buttons-row">
                <button
                  type="button"
                  className="choose-file-btn"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileImage size={18} />
                  <span>Choose from Files</span>
                </button>

                <button
                  type="button"
                  className="camera-file-btn"
                  onClick={() => cameraInputRef.current?.click()}
                >
                  <Camera size={18} />
                  <span>Open Camera</span>
                </button>
              </div>

              {/* Hidden file inputs */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic"
                className="hidden-input"
                onChange={handleFileChange}
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden-input"
                onChange={handleFileChange}
              />
            </div>
          ) : (
            /* Preview workspace when image is loaded */
            <div className="preview-container-card">
              <div className="preview-image-wrapper">
                <img src={previewUrl} alt="Tur leaf specimen" className="leaf-preview-img" />
              </div>

              <div className="preview-details-panel">
                <div className="file-info-header">
                  <div>
                    <h3 className="file-name" title={selectedFile.name}>
                      {selectedFile.name}
                    </h3>
                    <span className="file-meta">
                      Size: {formatFileSize(selectedFile.size)} &bull; Type: {selectedFile.type || 'Image'}
                    </span>
                  </div>

                  {!isProcessing && (
                    <button
                      type="button"
                      className="clear-file-btn"
                      onClick={handleClear}
                      title="Remove image and select another"
                      aria-label="Remove image"
                    >
                      <Trash2 size={18} />
                      <span>Remove</span>
                    </button>
                  )}
                </div>

                {/* Processing State Indicator */}
                {isProcessing && (
                  <div className="processing-progress-box">
                    <div className="progress-step-item">
                      <div className={`step-badge ${currentStep === 'uploading' ? 'badge-active' : 'badge-done'}`}>
                        {currentStep === 'uploading' ? <RefreshCw size={14} className="spinning" /> : <CheckCircle2 size={14} />}
                      </div>
                      <div className="step-text">
                        <strong>1. Storing image on server</strong>
                        <small>Uploading file to TurSathi secure repository...</small>
                      </div>
                    </div>

                    <div className="progress-step-item">
                      <div className={`step-badge ${currentStep === 'predicting' ? 'badge-active' : ''}`}>
                        {currentStep === 'predicting' ? <RefreshCw size={14} className="spinning" /> : <CheckCircle2 size={14} />}
                      </div>
                      <div className="step-text">
                        <strong>2. Running AI Leaf Gate & Neural Diagnosis</strong>
                        <small>Evaluating condition & calculating disease confidence...</small>
                      </div>
                    </div>
                  </div>
                )}

                {/* Action buttons */}
                {!isProcessing && (
                  <div className="start-analysis-row">
                    <button
                      type="button"
                      className="start-diagnosis-btn"
                      onClick={handleStartDiagnosis}
                    >
                      <span>Diagnose Tur Leaf</span>
                      <ArrowRight size={18} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Validation & API Error Feedback */}
          {validationError && (
            <div className="scan-alert alert-warning" role="alert">
              <AlertTriangle size={20} className="alert-icon" />
              <div>
                <strong>Validation Note</strong>
                <p>{validationError}</p>
              </div>
            </div>
          )}

          {apiError && (
            <div className="scan-alert alert-danger" role="alert">
              <XCircle size={20} className="alert-icon" />
              <div>
                <strong>Diagnostic Error</strong>
                <p>{apiError}</p>
              </div>
            </div>
          )}

          {/* Photography best practices reminder */}
          <div className="field-guidelines-box">
            <div className="guidelines-title">
              <Info size={18} />
              <span>Guidelines for Reliable Disease Detection</span>
            </div>
            <ul>
              <li>Capture leaves with visible symptoms (spots, wilting, mosaic patches, blight).</li>
              <li>Hold camera steady approximately 15–25 cm away from the leaf.</li>
              <li>Avoid capturing other crops, weeds, hands, or cluttered background objects.</li>
            </ul>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default Scan;
