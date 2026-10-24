import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Camera,
  CheckCircle2,
  Clock,
  ExternalLink,
  History,
  Leaf,
  Plus,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import { tokenService } from '../../services/tokenService.js';
import { scanService } from '../../services/scanService.js';
import './Home.css';

const SUPPORTED_CONDITIONS = [
  {
    name: 'Healthy Tur',
    localName: 'निरोगी तूर',
    description: 'Vibrant green leaf with no fungal lesions or chlorosis.',
    badgeClass: 'badge-healthy',
  },
  {
    name: 'Fusarium Wilt',
    localName: 'मर रोग (Fusarium udum)',
    description: 'Vascular browning, wilting, and yellowing of foliage.',
    badgeClass: 'badge-danger',
  },
  {
    name: 'Sterility Mosaic Disease',
    localName: 'वांझ रोग (SMD)',
    description: 'Mosaic mottling, smaller bushy leaves, and cessation of pod bearing.',
    badgeClass: 'badge-warning',
  },
  {
    name: 'Phytophthora Blight',
    localName: 'फायटोप्थोरा करपा',
    description: 'Water-soaked brownish-black lesions on stems and leaves.',
    badgeClass: 'badge-danger',
  },
  {
    name: 'Macrophomina Blight',
    localName: 'कोरडी मुळकूज / करपा',
    description: 'Dark sunken stem cankers and dry root necrosis.',
    badgeClass: 'badge-warning',
  },
];

export function Home() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [recentScans, setRecentScans] = useState([]);
  const [loadingScans, setLoadingScans] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const user = tokenService.getUser();
    setCurrentUser(user);
    loadRecentScans();
  }, []);

  const loadRecentScans = async () => {
    setLoadingScans(true);
    setError('');
    try {
      const data = await scanService.getScanHistory({ skip: 0, limit: 5 });
      const items = Array.isArray(data) ? data : data?.items || [];
      setRecentScans(items);
    } catch (err) {
      setError('Unable to load recent scans. Please check backend connection.');
    } finally {
      setLoadingScans(false);
    }
  };

  const farmerName = currentUser?.full_name || currentUser?.mobile_number || 'Farmer';

  return (
    <div className="home-page-layout">
      <Navbar />

      <main className="home-main-content">
        {/* Hero Greeting Section */}
        <section className="home-hero-banner">
          <div className="hero-content">
            <div className="hero-tag">
              <Leaf size={16} />
              <span>Pigeonpea (तूर) Health Companion</span>
            </div>
            <h1>Namaskar, {farmerName}!</h1>
            <p>
              Protect your Tur crop with instant AI leaf disease diagnosis, verified university spray prescriptions, and smart guidance.
            </p>

            <div className="hero-action-buttons">
              <Link to="/scan" className="primary-action-btn">
                <Camera size={20} />
                <span>Start New Scan</span>
              </Link>
              <Link to="/history" className="secondary-action-btn">
                <History size={20} />
                <span>View All Scans</span>
              </Link>
            </div>
          </div>

          <div className="hero-stats-card">
            <div className="stat-row">
              <span className="stat-label">Crop Season</span>
              <span className="stat-value highlight-gold">Kharif Tur 2026</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Crop Type</span>
              <span className="stat-value">Pigeonpea (Cajanus cajan)</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">AI Diagnostic Engine</span>
              <span className="stat-value highlight-green">Active (ResNet-50)</span>
            </div>
          </div>
        </section>

        {/* Quick Diagnostic Actions Grid */}
        <section className="quick-actions-section">
          <div className="action-card action-card-scan" onClick={() => navigate('/scan')}>
            <div className="action-icon-wrap icon-green">
              <Camera size={28} />
            </div>
            <div className="action-copy">
              <h3>Scan Tur Leaf</h3>
              <p>Capture or upload a photo of a symptomatic leaf for instant AI disease identification.</p>
            </div>
            <div className="action-arrow">
              <ArrowRight size={20} />
            </div>
          </div>

          <div className="action-card action-card-history" onClick={() => navigate('/history')}>
            <div className="action-icon-wrap icon-gold">
              <History size={28} />
            </div>
            <div className="action-copy">
              <h3>Scan History</h3>
              <p>Review previous diagnostic reports, disease severities, and spray advisories.</p>
            </div>
            <div className="action-arrow">
              <ArrowRight size={20} />
            </div>
          </div>
        </section>

        {/* Recent Scans Section */}
        <section className="recent-scans-section">
          <div className="section-header-row">
            <div>
              <h2>Recent Leaf Scans</h2>
              <p>Latest diagnostic findings recorded for your farm.</p>
            </div>
            <button
              type="button"
              className="refresh-btn"
              onClick={loadRecentScans}
              disabled={loadingScans}
              aria-label="Refresh recent scans"
            >
              <RefreshCw size={16} className={loadingScans ? 'spinning' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          {loadingScans ? (
            <div className="loading-state-card">
              <RefreshCw size={24} className="spinning" />
              <p>Checking latest scan records...</p>
            </div>
          ) : error ? (
            <div className="error-state-card">
              <ShieldAlert size={24} />
              <p>{error}</p>
              <button type="button" onClick={loadRecentScans} className="retry-btn">
                Try Again
              </button>
            </div>
          ) : recentScans.length === 0 ? (
            <div className="empty-scans-card">
              <div className="empty-icon-circle">
                <Leaf size={32} />
              </div>
              <h3>No Leaf Scans Yet</h3>
              <p>You haven't scanned any Tur crop leaves yet. Take a photo to get started with instant disease detection.</p>
              <Link to="/scan" className="primary-action-btn small-btn">
                <Plus size={18} />
                <span>Scan Your First Leaf</span>
              </Link>
            </div>
          ) : (
            <div className="scans-grid">
              {recentScans.map((scan) => {
                const disease = scan.disease_name || scan.predicted_label || 'Analysis Pending';
                const isHealthy = disease.toLowerCase().includes('healthy');
                const confidence = typeof scan.confidence === 'number' ? (scan.confidence * 100).toFixed(0) : null;
                const formattedDate = scan.created_at
                  ? new Date(scan.created_at).toLocaleDateString('en-IN', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })
                  : 'Recent';

                return (
                  <div
                    key={scan.scan_id || scan.id}
                    className="scan-summary-card"
                    onClick={() => navigate(`/result/${scan.scan_id || scan.id}`, { state: { scan } })}
                  >
                    <div className="scan-card-top">
                      <span className="scan-id-tag">Scan #{scan.scan_id || scan.id}</span>
                      <span className="scan-date">
                        <Clock size={12} />
                        {formattedDate}
                      </span>
                    </div>

                    <div className="scan-card-body">
                      <h4 className="scan-disease-title">{disease}</h4>
                      <div className="scan-meta-pills">
                        <span className={`status-pill ${isHealthy ? 'pill-healthy' : 'pill-disease'}`}>
                          {isHealthy ? 'Healthy Leaf' : 'Needs Attention'}
                        </span>
                        {confidence && (
                          <span className="confidence-pill">{confidence}% confidence</span>
                        )}
                      </div>
                    </div>

                    <div className="scan-card-footer">
                      <span className="view-details-link">
                        View Guidance <ArrowRight size={14} />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Supported Disease Reference */}
        <section className="supported-conditions-section">
          <div className="section-header-row">
            <div>
              <h2>Supported Pigeonpea Conditions</h2>
              <p>Trained neural network models detect these 5 specific field states.</p>
            </div>
          </div>

          <div className="conditions-grid">
            {SUPPORTED_CONDITIONS.map((cond) => (
              <div key={cond.name} className="condition-card">
                <div className="condition-header">
                  <span className={`condition-indicator ${cond.badgeClass}`} />
                  <h4>{cond.name}</h4>
                </div>
                <small className="condition-local-name">{cond.localName}</small>
                <p>{cond.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Photography Tips Card */}
        <section className="photography-tips-section">
          <div className="tips-card">
            <div className="tips-icon">
              <Sparkles size={28} />
            </div>
            <div className="tips-content">
              <h3>Field Photography Tips for Best Accuracy</h3>
              <ul>
                <li>Take photographs in natural bright daylight without strong shadows.</li>
                <li>Center a single Tur leaf within the frame against soil or neutral background.</li>
                <li>Ensure the camera lens is clean and focused so veins and spots are clear.</li>
                <li>Avoid blurry shots or extreme closeups that cut off the leaf edge.</li>
              </ul>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}

export default Home;
