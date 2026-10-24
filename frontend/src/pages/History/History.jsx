import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Calendar,
  Camera,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  History as HistoryIcon,
  Leaf,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import { scanService } from '../../services/scanService.js';
import './History.css';

const PAGE_SIZE = 10;

export function History() {
  const navigate = useNavigate();

  const [scans, setScans] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [filterType, setFilterType] = useState('all'); // 'all' | 'healthy' | 'disease'
  const [searchTerm, setSearchTerm] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchHistory(currentPage);
  }, [currentPage]);

  const fetchHistory = async (page) => {
    setLoading(true);
    setError('');

    const skip = (page - 1) * PAGE_SIZE;

    try {
      const data = await scanService.getScanHistory({ skip, limit: PAGE_SIZE });
      const items = Array.isArray(data) ? data : data?.items || [];
      const total = typeof data?.total === 'number' ? data.total : items.length;

      setScans(items);
      setTotalCount(total);
    } catch (err) {
      setError(err.detail || err.message || 'Unable to load scan history.');
    } finally {
      setLoading(false);
    }
  };

  // Filter & search
  const filteredScans = scans.filter((scan) => {
    const disease = (scan.disease_name || scan.predicted_label || '').toLowerCase();
    const isHealthy = disease.includes('healthy');

    // Filter type
    if (filterType === 'healthy' && !isHealthy) return false;
    if (filterType === 'disease' && isHealthy) return false;

    // Search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const idMatch = String(scan.scan_id || scan.id || '').includes(term);
      const nameMatch = disease.includes(term);
      return idMatch || nameMatch;
    }

    return true;
  });

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const healthyCount = scans.filter((s) =>
    (s.disease_name || s.predicted_label || '').toLowerCase().includes('healthy')
  ).length;

  const diseaseCount = scans.length - healthyCount;

  return (
    <div className="history-page-layout">
      <Navbar />

      <main className="history-main-content">
        {/* Header Section */}
        <div className="history-header-card">
          <div className="header-copy">
            <h1>Tur Leaf Scan History</h1>
            <p>Review past crop diagnostic reports, disease progressions, and treatment recommendations.</p>
          </div>

          <Link to="/scan" className="primary-action-btn">
            <Camera size={18} />
            <span>New Scan</span>
          </Link>
        </div>

        {/* Stats Row */}
        <div className="history-stats-bar">
          <div className="hist-stat-item">
            <span className="hist-stat-num">{totalCount}</span>
            <span className="hist-stat-lbl">Total Scans</span>
          </div>
          <div className="hist-stat-item">
            <span className="hist-stat-num text-healthy">{healthyCount}</span>
            <span className="hist-stat-lbl">Healthy Samples</span>
          </div>
          <div className="hist-stat-item">
            <span className="hist-stat-num text-disease">{diseaseCount}</span>
            <span className="hist-stat-lbl">Action Required</span>
          </div>
        </div>

        {/* Controls: Search & Filter Tabs */}
        <div className="history-controls-row">
          <div className="search-input-wrap">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Search by Scan # or Disease name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-tabs">
            <button
              type="button"
              className={`filter-tab ${filterType === 'all' ? 'active' : ''}`}
              onClick={() => setFilterType('all')}
            >
              All Scans
            </button>
            <button
              type="button"
              className={`filter-tab ${filterType === 'healthy' ? 'active' : ''}`}
              onClick={() => setFilterType('healthy')}
            >
              Healthy
            </button>
            <button
              type="button"
              className={`filter-tab ${filterType === 'disease' ? 'active' : ''}`}
              onClick={() => setFilterType('disease')}
            >
              Diseases
            </button>
          </div>
        </div>

        {/* Content Area */}
        {loading ? (
          <div className="history-loading-card">
            <RefreshCw size={28} className="spinning" />
            <p>Loading scan records...</p>
          </div>
        ) : error ? (
          <div className="history-error-card">
            <ShieldAlert size={32} />
            <h3>Unable to Retrieve Scan History</h3>
            <p>{error}</p>
            <button type="button" className="retry-btn" onClick={() => fetchHistory(currentPage)}>
              Retry Connection
            </button>
          </div>
        ) : filteredScans.length === 0 ? (
          <div className="history-empty-card">
            <div className="empty-icon-wrap">
              <HistoryIcon size={36} />
            </div>
            {searchTerm || filterType !== 'all' ? (
              <>
                <h3>No Matching Records</h3>
                <p>No scans match your search or filter. Try clearing the filters to see all scans.</p>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setFilterType('all');
                    setSearchTerm('');
                  }}
                >
                  Clear Filters
                </button>
              </>
            ) : (
              <>
                <h3>No Scans Recorded Yet</h3>
                <p>You haven't scanned any Tur crop leaves yet. Take a photograph of a Tur leaf to start diagnostic tracking.</p>
                <Link to="/scan" className="primary-action-btn">
                  <Plus size={18} />
                  <span>Scan First Leaf</span>
                </Link>
              </>
            )}
          </div>
        ) : (
          <div className="history-list-container">
            {filteredScans.map((scan) => {
              const id = scan.scan_id || scan.id;
              const disease = scan.disease_name || scan.predicted_label || 'Analysis Pending';
              const isHealthy = disease.toLowerCase().includes('healthy');
              const confidence =
                typeof scan.confidence === 'number' ? (scan.confidence * 100).toFixed(0) : null;
              const formattedDate = scan.created_at
                ? new Date(scan.created_at).toLocaleDateString('en-IN', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'Recent';

              return (
                <div
                  key={id}
                  className="history-item-card"
                  onClick={() => navigate(`/result/${id}`, { state: { scan } })}
                >
                  <div className="history-item-left">
                    <div className={`condition-indicator-icon ${isHealthy ? 'icon-healthy' : 'icon-disease'}`}>
                      <Leaf size={22} />
                    </div>

                    <div className="history-item-meta">
                      <div className="item-title-row">
                        <span className="item-id-tag">Scan #{id}</span>
                        <h3 className="item-disease-name">{disease}</h3>
                      </div>

                      <div className="item-date-row">
                        <Clock size={13} />
                        <span>{formattedDate}</span>
                        {scan.severity && (
                          <span className="item-severity-pill">Severity: {scan.severity}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="history-item-right">
                    {confidence && (
                      <span className="confidence-badge">{confidence}% confidence</span>
                    )}
                    <span className={`status-badge ${isHealthy ? 'badge-healthy' : 'badge-disease'}`}>
                      {isHealthy ? 'Healthy Leaf' : 'Advisory Ready'}
                    </span>
                    <ArrowRight size={18} className="item-arrow" />
                  </div>
                </div>
              );
            })}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="history-pagination">
                <button
                  type="button"
                  className="page-btn"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  aria-label="Previous page"
                >
                  <ChevronLeft size={18} />
                  <span>Previous</span>
                </button>

                <span className="page-indicator">
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  type="button"
                  className="page-btn"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  aria-label="Next page"
                >
                  <span>Next</span>
                  <ChevronRight size={18} />
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

export default History;
