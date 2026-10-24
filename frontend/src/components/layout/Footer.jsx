import { AlertCircle, Shield } from 'lucide-react';
import './Footer.css';

export function Footer() {
  return (
    <footer className="tursathi-footer">
      <div className="footer-container">
        <div className="footer-disclaimer">
          <div className="disclaimer-header">
            <Shield size={18} className="shield-icon" />
            <strong>Agricultural Safety & Advisory Disclaimer</strong>
          </div>
          <p>
            TurSathi AI provides crop advisory and diagnosis based on machine learning models and verified agricultural guidance (ICAR / Vasantrao Naik Marathwada Krishi Vidyapeeth). Always inspect crop leaves closely, strictly follow pesticide container label instructions, observe recommended pre-harvest intervals, and use recommended personal protective equipment (PPE). Never apply chemical treatments to healthy crops.
          </p>
        </div>

        <div className="footer-bottom">
          <div className="footer-brand">
            <span>TurSathi AI</span> &bull; <em>Healthy Tur, Prosperous Farmers</em>
          </div>
          <div className="footer-copy">
            &copy; {new Date().getFullYear()} TurSathi AI. Dedicated to Indian Pigeonpea (तूर) Farmers.
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
