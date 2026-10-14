# STAGE F29 REPORT: FRONTEND/BACKEND FUNCTIONAL REGRESSION AUDIT

**Project:** TurSathi AI / AgriMind AI — Pigeonpea Disease Detection  
**Stage:** F29 (Frontend/Backend Functional Regression)  
**Execution Timestamp:** 2026-10-13T13:44:00+05:30  
**Status:** COMPLETE (Build verified, API contracts validated, regression clean)

---

### 1. Frontend Build & Asset Verification

1. **Vite Production Build:**
   - Command executed: `npm run build` in `frontend/`.
   - Result: **SUCCESS** (Exit code 0, completed in 1.59s).
   - Bundled output artifacts:
     - `dist/index.html` (440 bytes)
     - `dist/assets/index-ON6Tq5DK.css` (20.66 kB │ gzip: 5.33 kB)
     - `dist/assets/index-Z8DWxB_M.js` (286.14 kB │ gzip: 88.53 kB)
   - Diagnostic observations: Minor runtime-resolution notices for CSS background image fallbacks (`splash-bg.jpg`, `login-bg.jpg`, `register-bg.jpg`), gracefully cushioned by radial and linear background gradients in CSS rules.

2. **Application Architecture & Component Audit:**
   - **Web Application (`frontend/`):** React 19 + Vite app serving `Splash`, `Login`, and `Register` pages with trilingual localization (English, Hindi, Marathi) and responsive viewport styling.
   - **Field Mobile Application (`mobile/`):** React Native / Expo application providing camera capture, image upload (`uploadScanImage`), ML disease prediction (`predictTurLeaf`), voice report recordings, and verified spray recommendations. Currently executing active Expo development server (`npx expo start --clear --lan`).

---

### 2. Functional Regression Matrix

| Feature / Workflow | Client Component | Backend Contract | Verified Behavior | Status |
| :--- | :--- | :--- | :--- | :---: |
| **User Registration** | `Register.jsx` / Mobile Auth | `POST /api/v1/auth/register` | Normalizes email/mobile, enforces password rules, returns JWT token (201). Rejects duplicate mobile numbers (400). | **PASS** |
| **User Authentication** | `Login.jsx` / Mobile Auth | `POST /api/v1/auth/login` | Accepts email or mobile identifier, validates credentials, issues JWT bearer token (200). | **PASS** |
| **Image Upload Intake** | `scanApi.ts` (`uploadScanImage`) | `POST /api/v1/scans` | Multipart upload validated for MIME and size ($\le 20\text{ MB}$). UUID-isolated storage key assigned; returns `scan_id` (201). | **PASS** |
| **Image Gate Rejection** | `scanApi.ts` (`classifyHttpError`) | `POST /api/v1/predictions/tur-leaf/{scan_id}` | Non-tur leaves safely caught by `TurImageGate`. Returns HTTP 422 with `"Please upload a clear Tur/Pigeonpea leaf image."` | **PASS** |
| **Disease Prediction** | `scanApi.ts` (`predictTurLeaf`) | `POST /api/v1/predictions/tur-leaf/{scan_id}` | Returns HTTP 200 with completed status, disease name, confidence score, and severity level. | **PASS** |
| **Five-Class Mapping** | Mobile Result Screen | `TurDiseasePredictor` | Prediction strictly conforms to: `Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`, `Wilt`. | **PASS** |
| **Scan History Retrieval** | Scan History Screen | `GET /api/v1/scans/{scan_id}` | Full scan detail retrieved with timestamps, persisted diagnosis, and strict multi-tenant ownership (403/404). | **PASS** |
| **Spray Guidance Lookup** | Recommendation Screen | `GET /api/v1/recommendations/tur/{disease}/spray-guidance` | Safe 404 return when guidance unseeded; never fabricates unverified pesticide data. | **PASS** |
| **Corrupted File Guard** | Intake + Gate | `TurImageGate.validate()` | Traps non-image bytes and small images ($< 32 \times 32$), updates scan status to `"rejected"`, raises clean 422. | **PASS** |

---

### 3. Error Presentation & User Guidance

Both the web and mobile interfaces implement structured error handlers:
- **Image Rejections (HTTP 422):** Render friendly guidance informing farmers that the photo is not recognized as a Tur leaf and prompting them to take a clearer shot.
- **Low Confidence Guard ($< 0.65$):** Backend marks the condition as unsupported and advises consulting local agricultural extension workers.
- **Network Timeouts:** Client implements 30-second image upload and 60-second voice upload timeouts with retry prompts.

---

### 4. Regression Conclusion

All existing routes, components, and contracts remain stable and intact. No regressions were introduced, and zero production modifications were required.
