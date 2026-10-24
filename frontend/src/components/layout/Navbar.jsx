import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import {
  Camera,
  History,
  Home,
  LogOut,
  Menu,
  ShieldCheck,
  User,
  X,
} from 'lucide-react';
import { authService } from '../../services/authService.js';
import { tokenService } from '../../services/tokenService.js';
import './Navbar.css';

export function Navbar() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const currentUser = tokenService.getUser();

  const handleLogout = () => {
    authService.logout();
    navigate('/login', { replace: true });
  };

  const displayName = currentUser?.full_name || currentUser?.mobile_number || 'Farmer';

  return (
    <header className="tursathi-navbar">
      <div className="navbar-container">
        {/* Brand */}
        <Link to="/home" className="navbar-brand" aria-label="TurSathi AI Home">
          <div className="nav-brand-mark" aria-hidden="true">
            <span className="nav-leaf nav-leaf-a" />
            <span className="nav-leaf nav-leaf-b" />
            <span className="nav-leaf nav-leaf-c" />
            <span className="nav-stem" />
          </div>
          <div className="nav-brand-text">
            <span className="brand-green">Tur</span>
            <span className="brand-gold">Sathi</span>
            <span className="brand-green brand-ai">AI</span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="navbar-links" aria-label="Primary navigation">
          <NavLink
            to="/home"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Home size={18} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/scan"
            className={({ isActive }) => `nav-link nav-link-scan ${isActive ? 'active' : ''}`}
          >
            <Camera size={18} />
            <span>Scan Crop</span>
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <History size={18} />
            <span>Scan History</span>
          </NavLink>
        </nav>

        {/* User Profile & Actions */}
        <div className="navbar-actions">
          <div className="user-badge" title={displayName}>
            <div className="user-avatar" aria-hidden="true">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="user-info">
              <span className="user-greeting">Namaskar,</span>
              <span className="user-name">{displayName}</span>
            </div>
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
            title="Logout from TurSathi AI"
            aria-label="Logout"
          >
            <LogOut size={18} />
            <span className="logout-text">Logout</span>
          </button>

          {/* Mobile hamburger toggle */}
          <button
            type="button"
            className="mobile-toggle"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <div className="mobile-menu-drawer">
          <NavLink
            to="/home"
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <Home size={20} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/scan"
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <Camera size={20} />
            <span>Scan Crop</span>
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileMenuOpen(false)}
          >
            <History size={20} />
            <span>Scan History</span>
          </NavLink>

          <button
            type="button"
            className="mobile-logout-button"
            onClick={() => {
              setMobileMenuOpen(false);
              handleLogout();
            }}
          >
            <LogOut size={20} />
            <span>Logout ({displayName})</span>
          </button>
        </div>
      )}
    </header>
  );
}

export default Navbar;
