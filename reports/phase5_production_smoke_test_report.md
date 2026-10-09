# PHASE 5I: PRODUCTION SMOKE TEST REPORT

## 1. Setup
- Executed `phase5_smoke_test.py` against the fully initialized FastAPI application state.
- Passed unmocked, physical image files into the prediction endpoint (`POST /api/v1/predictions/tur-leaf/{scan_id}`).

## 2. Test Cases & Results

| Case | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | Known Tur Image (V3 Test Set) | Validator = Tur<br>Disease predictor = CALLED<br>HTTP = 200 | Validator = Tur<br>Disease = Healthy (0.999)<br>HTTP = 200 | PASSED |
| 2 | Known Not_Tur Image (V3 Test Set) | Validator = Not_Tur<br>Disease predictor = NOT CALLED<br>HTTP = 422 | Validator = Not_Tur<br>Message: "Please upload a clear Tur/Pigeonpea leaf image."<br>HTTP = 422 | PASSED |
| 3 | Invalid Image (Corrupt Bytes) | Safe rejection<br>Disease predictor = NOT CALLED<br>HTTP = 422 | Reason: corrupted_image<br>Message: "Please upload a clear Tur/Pigeonpea leaf image."<br>HTTP = 422 | PASSED |
| 4 | Known Tur (Frozen Real-World) | Validator = Tur<br>Disease predictor = CALLED<br>HTTP = 200 | Validator = Tur<br>Disease = Wilt (1.00)<br>HTTP = 200 | PASSED |
| 5 | Known Not_Tur (Frozen Real-World) | Validator = Not_Tur<br>Disease predictor = NOT CALLED<br>HTTP = 422 | Validator = Not_Tur<br>Message: "Please upload a clear Tur/Pigeonpea leaf image."<br>HTTP = 422 | PASSED |

## 3. Conclusion
- The live integrated API behaves exactly as specified.
- The `TurImageGate` safely halts processing and returns the user-friendly HTTP 422 message without leaking internal tracebacks or exposing the disease model to out-of-domain images.
- Integration is mechanically successful.
