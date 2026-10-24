import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle,
  CheckCircle2,
  ChevronRight,
  Droplet,
  FileText,
  Heart,
  Home,
  Info,
  Printer,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import { scanService } from '../../services/scanService.js';
import { recommendationService } from '../../services/recommendationService.js';
import './Result.css';

export function Result() {
  const { scanId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [scan, setScan] = useState(location.state?.scan || null);
  const [imagePreview, setImagePreview] = useState(location.state?.imagePreview || null);
  const [sprayGuidance, setSprayGuidance] = useState(null);
  const [aiGuidance, setAiGuidance] = useState(null);

  const [loading, setLoading] = useState(!location.state?.scan);
  const [loadingGuidance, setLoadingGuidance] = useState(false);
  const [error, setError] = useState('');

  // 1. Fetch scan detail if not passed via location state
  useEffect(() => {
    async function fetchScanData() {
      if (scan && scan.disease_name) {
        // Already have scan data, proceed to load guidance
        loadGuidance(scan);
        return;
      }

      if (!scanId) {
        setError('No scan identifier provided.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const data = await scanService.getScanDetail(scanId);
        setScan(data);
        loadGuidance(data);
      } catch (err) {
        setError(err.detail || err.message || 'Unable to retrieve scan diagnosis.');
      } finally {
        setLoading(false);
      }
    }

    fetchScanData();
  }, [scanId]);

  // 2. Fetch verified spray guidance & secondary AI guidance for disease
  const loadGuidance = async (scanData) => {
    const disease = scanData?.disease_name;
    if (!disease) return;

    setLoadingGuidance(true);

    // Fetch verified university spray guidance
    try {
      const guidance = await recommendationService.getTurSprayGuidance(disease);
      setSprayGuidance(guidance);
    } catch (err) {
      // 404 means verified guidance not available yet for this condition
      setSprayGuidance(null);
    }

    // Attempt secondary AI guidance if scanId is available
    const id = scanData.scan_id || scanId;
    if (id) {
      try {
        const ai = await scanService.getAiGuidance(id, 'en');
        setAiGuidance(ai);
      } catch {
        // AI guidance optional secondary layer
        setAiGuidance(null);
      }
    }

    setLoadingGuidance(false);
  };

  const diseaseName = scan?.disease_name || scan?.predicted_label || 'Analysis in Progress';
  const isHealthy = diseaseName.toLowerCase().includes('healthy');
  const confidenceVal = typeof scan?.confidence === 'number' ? scan.confidence : null;
  const confidencePercent = confidenceVal !== null ? (confidenceVal * 100).toFixed(1) : null;
  const isLowConfidence = confidenceVal !== null && confidenceVal < 0.65;
  const severity = scan?.severity || (isHealthy ? 'Healthy' : 'Needs Assessment');

  const getSeverityBadgeClass = (sev) => {
    const s = (sev || '').toLowerCase();
    if (s.includes('healthy')) return 'sev-healthy';
    if (s.includes('mild') || s.includes('low')) return 'sev-mild';
    if (s.includes('mod')) return 'sev-moderate';
    if (s.includes('sev') || s.includes('high')) return 'sev-severe';
    return 'sev-moderate';
  };

  return (
    <div className="result-page-layout">
      <Navbar />

      <main className="result-main-content">
        {/* Navigation Breadcrumb */}
        <div className="result-breadcrumb">
          <Link to="/home" className="breadcrumb-link">
            <Home size={14} />
            <span>Dashboard</span>
          </Link>
          <ChevronRight size={14} />
          <Link to="/history" className="breadcrumb-link">
            History
          </Link>
          <ChevronRight size={14} />
          <span className="breadcrumb-current">Scan #{scan?.scan_id || scanId || 'Result'}</span>
        </div>

        {loading ? (
          <div className="result-loading-card">
            <RefreshCw size={32} className="spinning" />
            <h2>Loading Diagnostic Report...</h2>
            <p>Retrieving neural model predictions and verified agricultural spray guidance.</p>
          </div>
        ) : error ? (
          <div className="result-error-card">
            <ShieldAlert size={36} />
            <h2>Unable to Load Diagnosis</h2>
            <p>{error}</p>
            <div className="result-btn-row">
              <button type="button" className="btn-secondary" onClick={() => navigate('/scan')}>
                <Camera size={16} />
                <span>Try Another Scan</span>
              </button>
              <button type="button" className="btn-primary" onClick={() => navigate('/home')}>
                <span>Return to Dashboard</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="result-container">
            {/* Top Diagnostic Summary Banner */}
            <div className={`diagnostic-hero-card ${isHealthy ? 'hero-healthy' : 'hero-disease'}`}>
              <div className="hero-status-row">
                <span className="crop-pill">Crop: Tur (तूर)</span>
                <span className={`severity-pill ${getSeverityBadgeClass(severity)}`}>
                  Severity: {severity}
                </span>
                {scan?.scan_id && (
                  <span className="scan-ref">Scan ID: #{scan.scan_id}</span>
                )}
              </div>

              <div className="hero-main-title">
                <div className="condition-icon-badge">
                  {isHealthy ? <CheckCircle2 size={36} /> : <AlertCircle size={36} />}
                </div>
                <div>
                  <h1 className="condition-heading">{diseaseName}</h1>
                  <p className="condition-subheading">
                    {isHealthy
                      ? 'No disease symptoms detected on this leaf specimen.'
                      : 'Fungal or viral symptoms detected by Tur disease neural model.'}
                  </p>
                </div>
              </div>

              {/* Confidence Score Bar */}
              {confidencePercent && (
                <div className="confidence-meter-container">
                  <div className="confidence-label-row">
                    <span>Diagnostic Confidence</span>
                    <strong>{confidencePercent}%</strong>
                  </div>
                  <div className="meter-track">
                    <div
                      className={`meter-fill ${isLowConfidence ? 'meter-low' : 'meter-good'}`}
                      style={{ width: `${Math.min(Number(confidencePercent), 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Low-Confidence Warning Banner (if < 65%) */}
            {isLowConfidence && (
              <div className="low-confidence-banner" role="alert">
                <AlertTriangle size={24} className="banner-icon" />
                <div className="banner-text">
                  <strong>Low Model Confidence Advisory (&lt; 65%)</strong>
                  <p>
                    The prediction confidence for this sample is below the high-reliability threshold. Symptoms may be early-stage or the lighting may be suboptimal. We recommend repeating the scan with clearer lighting or consulting your local Taluka Agricultural Officer or KVK specialist before applying chemical sprays.
                  </p>
                </div>
              </div>
            )}

            {/* Specimen image preview (if available) */}
            {imagePreview && (
              <div className="specimen-preview-box">
                <div className="specimen-header">
                  <FileText size={16} />
                  <span>Captured Leaf Specimen</span>
                </div>
                <div className="specimen-img-wrap">
                  <img src={imagePreview} alt="Tur leaf specimen" />
                </div>
              </div>
            )}

            {/* Verified Agricultural Recommendations */}
            {sprayGuidance ? (
              <section className="spray-guidance-section">
                <div className="section-title-wrap">
                  <ShieldCheck size={22} className="verified-shield-icon" />
                  <div>
                    <h2>Verified Agricultural Advisory</h2>
                    <small>Official guidance sourced from state agricultural university recommendations.</small>
                  </div>
                </div>

                {sprayGuidance.important_alert && (
                  <div className="important-alert-banner">
                    <AlertCircle size={20} />
                    <div>
                      <strong>Important Notice:</strong> {sprayGuidance.important_alert}
                    </div>
                  </div>
                )}

                {/* Practical Spray Actions */}
                {sprayGuidance.spray_guidance && sprayGuidance.spray_guidance.length > 0 && (
                  <div className="guidance-card">
                    <div className="card-heading">
                      <Droplet size={18} />
                      <h3>Recommended Spray Treatment</h3>
                    </div>
                    <ol className="guidance-list numbered-list">
                      {sprayGuidance.spray_guidance.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Safety & PPE Precautions */}
                {sprayGuidance.safety_precautions && sprayGuidance.safety_precautions.length > 0 && (
                  <div className="guidance-card">
                    <div className="card-heading">
                      <Shield size={18} />
                      <h3>Safety & Protective Measures</h3>
                    </div>
                    <ul className="guidance-list bulleted-list">
                      {sprayGuidance.safety_precautions.map((safe, idx) => (
                        <li key={idx}>{safe}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Post-Spraying Advisory */}
                {sprayGuidance.after_spraying && sprayGuidance.after_spraying.length > 0 && (
                  <div className="guidance-card">
                    <div className="card-heading">
                      <CheckCircle size={18} />
                      <h3>Post-Spraying Observation</h3>
                    </div>
                    <ul className="guidance-list bulleted-list">
                      {sprayGuidance.after_spraying.map((post, idx) => (
                        <li key={idx}>{post}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Farmer Next Step */}
                {sprayGuidance.farmer_action && (
                  <div className="guidance-card highlight-action-card">
                    <div className="card-heading">
                      <Sparkles size={18} />
                      <h3>Action for Farmer</h3>
                    </div>
                    <p className="farmer-action-text">{sprayGuidance.farmer_action}</p>
                  </div>
                )}
              </section>
            ) : isHealthy ? (
              /* Healthy Leaf Guidance Card */
              <div className="healthy-leaf-card">
                <div className="card-heading">
                  <CheckCircle2 size={24} className="healthy-icon" />
                  <h3>No Chemical Treatment Required</h3>
                </div>
                <p>
                  Your Tur crop foliage demonstrates healthy leaf architecture with normal chlorophyl expression. Maintain balanced N:P:K fertilization, monitor moisture levels, and conduct weekly scouting. Do not spray fungicides or chemical pesticides on healthy crops.
                </p>
              </div>
            ) : (
              /* When specific guidance is pending backend update */
              <div className="guidance-card neutral-info-card">
                <div className="card-heading">
                  <Info size={18} />
                  <h3>Treatment Protocol</h3>
                </div>
                <p>
                  Diagnostic report generated successfully. Verified spray guidance for this specific strain is being updated in the university reference database. Please consult your local Krishi Vigyan Kendra (KVK) for localized chemical formulations.
                </p>
              </div>
            )}

            {/* AI Explanation Layer (if returned by Claude guidance) */}
            {aiGuidance?.disease_explanation && (
              <div className="ai-explanation-box">
                <div className="ai-heading">
                  <Sparkles size={18} />
                  <h3>Diagnostic Insights & Explanation</h3>
                </div>
                <p>{aiGuidance.disease_explanation}</p>
              </div>
            )}

            {/* Mandatory Agricultural Disclaimer */}
            <div className="safety-disclaimer-box">
              <ShieldAlert size={18} className="disclaimer-alert-icon" />
              <p>
                <strong>Statutory Agricultural Safety Disclaimer:</strong> Chemical dosage must adhere to registered CIBRC (Central Insecticides Board & Registration Committee) and state agricultural university label claims. Always calibrate spray pumps, spray in early morning or evening to protect honeybee pollinators, and never inhale or mix agrochemicals without protective masks and gloves.
              </p>
            </div>

            {/* Action Buttons Row */}
            <div className="result-actions-bar">
              <button
                type="button"
                className="btn-print"
                onClick={() => window.print()}
                title="Print this advisory"
              >
                <Printer size={16} />
                <span>Print Report</span>
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={() => navigate('/history')}
              >
                <span>View History</span>
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={() => navigate('/scan')}
              >
                <Camera size={16} />
                <span>Scan Another Leaf</span>
              </button>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

export default Result;
