import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { tokenService } from '../../services/tokenService.js';
import './Splash.css';

function Splash() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(12);

  const proceed = () => {
    const destination = tokenService.isAuthenticated() ? '/home' : '/login';
    navigate(destination, { replace: true });
  };

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((current) => {
        if (current >= 100) {
          clearInterval(timer);
          setTimeout(proceed, 200);
          return 100;
        }

        return Math.min(current + 4, 100);
      });
    }, 60);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="splash-screen">
      <div className="splash-scene" aria-label="TurSathi AI splash screen" onClick={proceed} style={{ cursor: 'pointer' }}>
        <div className="status-bar">
          <span className="time">9:41</span>
          <div className="status-icons" aria-hidden="true">
            <span className="signal" />
            <span className="wifi" />
            <span className="battery" />
          </div>
        </div>

        <div className="brand-wrap">
          <div className="brand-mark" aria-hidden="true">
            <span className="leaf leaf-a" />
            <span className="leaf leaf-b" />
            <span className="leaf leaf-c" />
            <span className="stem" />
          </div>

          <h1 className="brand-name" aria-label="TurSathi AI branding">
            <span className="brand-green">Tur</span>
            <span className="brand-gold">Sathi</span>
            <span className="brand-green brand-ai">AI</span>
          </h1>
        </div>

        <div className="tagline-block">
          <span>Healthy Tur</span>
          <span>Prosperous Farmers</span>
        </div>

        <div className="benefits-row" aria-label="TurSathi AI value points">
          <div className="benefit-item">
            <div className="icon-wrap">
              <span className="leaf-dot" />
            </div>
            <span>Detect Diseases Early</span>
          </div>

          <div className="benefit-item">
            <div className="icon-wrap">
              <span className="brain-icon" />
            </div>
            <span>Get Expert AI Guidance</span>
          </div>

          <div className="benefit-item">
            <div className="icon-wrap">
              <span className="chart-icon" />
            </div>
            <span>Increase Your Yield</span>
          </div>
        </div>

        <div className="field-visual" aria-hidden="true">
          <div className="sun-glow" />
          <div className="mountain mountain-back" />
          <div className="mountain mountain-front" />
          <div className="field-land" />
          <div className="field-lines field-lines-1" />
          <div className="field-lines field-lines-2" />
          <div className="field-lines field-lines-3" />
          <div className="farmer-figure">
            <div className="head" />
            <div className="body" />
            <div className="turban" />
            <div className="sash" />
          </div>
        </div>

        <div className="loading-panel">
          <div className="progress-track" aria-label="Loading progress">
            <span className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <p>Growing a Smarter Tomorrow...</p>
          <div className="pager-dots" aria-hidden="true">
            <span className="dot active" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Splash;
