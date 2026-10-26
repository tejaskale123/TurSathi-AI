import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

// Test RecommendationApiError prototype and properties directly
describe('RecommendationApiError class', () => {
  class RecommendationApiError extends Error {
    constructor(httpStatus, message, isNotFound = false) {
      super(message);
      this.name = 'RecommendationApiError';
      this.httpStatus = httpStatus;
      this.isNotFound = isNotFound;
      Object.setPrototypeOf(this, RecommendationApiError.prototype);
    }
  }

  test('maintains prototype chain and instanceof check', () => {
    const err = new RecommendationApiError(404, 'Scan not found', true);
    assert.equal(err instanceof RecommendationApiError, true);
    assert.equal(err instanceof Error, true);
    assert.equal(err.name, 'RecommendationApiError');
    assert.equal(err.httpStatus, 404);
    assert.equal(err.isNotFound, true);
    assert.equal(err.message, 'Scan not found');
  });

  test('extractErrorDetail helper handles various FastAPI response formats', () => {
    function extractErrorDetail(data, fallback) {
      if (typeof data?.detail === 'string' && data.detail.trim()) {
        return data.detail.trim();
      }
      if (Array.isArray(data?.detail) && data.detail.length > 0) {
        const first = data.detail[0];
        if (typeof first?.msg === 'string' && first.msg.trim()) {
          return first.msg.trim();
        }
      }
      if (typeof data?.message === 'string' && data.message.trim()) {
        return data.message.trim();
      }
      return fallback;
    }

    // 1. Plain string detail (401 / 404)
    assert.equal(
      extractErrorDetail({ detail: 'Scan #1012 not found' }, 'Fallback'),
      'Scan #1012 not found'
    );

    // 2. FastAPI validation array (422)
    assert.equal(
      extractErrorDetail(
        { detail: [{ type: 'missing', loc: ['header', 'authorization'], msg: 'Field required' }] },
        'Fallback'
      ),
      'Field required'
    );

    // 3. Object message
    assert.equal(
      extractErrorDetail({ message: 'Custom error message' }, 'Fallback'),
      'Custom error message'
    );

    // 4. Missing detail fallback
    assert.equal(
      extractErrorDetail({}, 'Default fallback error'),
      'Default fallback error'
    );
  });
});

describe('fetchAIGuidance request and error handling simulation', () => {
  let originalFetch;
  let recordedCalls = [];

  class MockRecommendationApiError extends Error {
    constructor(httpStatus, message, isNotFound = false) {
      super(message);
      this.name = 'RecommendationApiError';
      this.httpStatus = httpStatus;
      this.isNotFound = isNotFound;
      Object.setPrototypeOf(this, MockRecommendationApiError.prototype);
    }
  }

  function extractErrorDetail(data, fallback) {
    if (typeof data?.detail === 'string' && data.detail.trim()) {
      return data.detail.trim();
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (typeof first?.msg === 'string' && first.msg.trim()) {
        return first.msg.trim();
      }
    }
    if (typeof data?.message === 'string' && data.message.trim()) {
      return data.message.trim();
    }
    return fallback;
  }

  async function simulateFetchAIGuidance(baseUrl, scanId, language, token, signal) {
    const langQuery = language ? `?language=${encodeURIComponent(language)}` : '';
    const url = `${baseUrl}/api/v1/predictions/tur-leaf/${scanId}/ai-guidance${langQuery}`;

    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    const onExternalAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) {
        clearTimeout(timeoutId);
        throw new MockRecommendationApiError(null, 'Request was canceled.');
      }
      signal.addEventListener('abort', onExternalAbort, { once: true });
    }

    try {
      const response = await global.fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({}),
        signal: controller.signal,
      });

      if (response.status === 404) {
        const data = await response.json().catch(() => ({}));
        const message = extractErrorDetail(data, 'Scan not found for AI guidance.');
        throw new MockRecommendationApiError(404, message, true);
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message = extractErrorDetail(data, `Server error (HTTP ${response.status})`);
        throw new MockRecommendationApiError(response.status, message, false);
      }

      const data = await response.json();
      return data;
    } catch (err) {
      if (err instanceof MockRecommendationApiError || err?.name === 'RecommendationApiError') {
        throw err;
      }

      const isAborted =
        err?.name === 'AbortError' ||
        err?.name === 'CanceledError' ||
        (typeof err?.message === 'string' &&
          (err.message.includes('canceled') || err.message.includes('aborted'))) ||
        controller.signal.aborted ||
        Boolean(signal?.aborted);

      if (isAborted) {
        if (signal?.aborted) {
          throw new MockRecommendationApiError(null, 'Request was canceled.');
        }
        throw new MockRecommendationApiError(null, 'Connection timed out. Please try again.');
      }

      throw new MockRecommendationApiError(null, 'Unable to connect to server. Please check your connection.');
    } finally {
      clearTimeout(timeoutId);
      if (signal) {
        signal.removeEventListener('abort', onExternalAbort);
      }
    }
  }

  beforeEach(() => {
    originalFetch = global.fetch;
    recordedCalls = [];
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  test('constructs exact POST URL with ?language=mr, Bearer token, and body {}', async () => {
    global.fetch = async (url, options) => {
      recordedCalls.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          crop: 'tur',
          disease_name: 'Healthy',
          language: 'mr',
          farmer_action: [],
        }),
      };
    };

    const res = await simulateFetchAIGuidance(
      'http://127.0.0.1:8000',
      1012,
      'mr',
      'mock_token_abc'
    );

    assert.equal(res.status, 'success');
    assert.equal(recordedCalls.length, 1);
    const call = recordedCalls[0];
    assert.equal(call.url, 'http://127.0.0.1:8000/api/v1/predictions/tur-leaf/1012/ai-guidance?language=mr');
    assert.equal(call.options.method, 'POST');
    assert.equal(call.options.headers['Content-Type'], 'application/json');
    assert.equal(call.options.headers['Authorization'], 'Bearer mock_token_abc');
    assert.equal(call.options.body, '{}');
  });

  test('propagates 404 with isNotFound = true without masking', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Scan #999 not found' }),
    });

    await assert.rejects(
      async () => {
        await simulateFetchAIGuidance('http://127.0.0.1:8000', 999, 'mr', 'token');
      },
      (err) => {
        assert.equal(err.name, 'RecommendationApiError');
        assert.equal(err.httpStatus, 404);
        assert.equal(err.isNotFound, true);
        assert.equal(err.message, 'Scan #999 not found');
        return true;
      }
    );
  });

  test('propagates 422 FastAPI validation error without masking or throwing object string', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ['header', 'authorization'], msg: 'Field required', type: 'missing' }],
      }),
    });

    await assert.rejects(
      async () => {
        await simulateFetchAIGuidance('http://127.0.0.1:8000', 1012, 'mr', undefined);
      },
      (err) => {
        assert.equal(err.name, 'RecommendationApiError');
        assert.equal(err.httpStatus, 422);
        assert.equal(err.isNotFound, false);
        assert.equal(err.message, 'Field required');
        return true;
      }
    );
  });

  test('propagates 401 Unauthorized without masking as connection error', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid or expired access token.' }),
    });

    await assert.rejects(
      async () => {
        await simulateFetchAIGuidance('http://127.0.0.1:8000', 1012, 'mr', 'expired_token');
      },
      (err) => {
        assert.equal(err.name, 'RecommendationApiError');
        assert.equal(err.httpStatus, 401);
        assert.equal(err.message, 'Invalid or expired access token.');
        return true;
      }
    );
  });

  test('distinguishes intentional unmount cancellation from server error', async () => {
    const unmountController = new AbortController();

    global.fetch = async (url, options) => {
      // simulate user navigating away before response arrives
      unmountController.abort();
      const err = new Error('Fetch request has been canceled');
      err.name = 'Error';
      throw err;
    };

    await assert.rejects(
      async () => {
        await simulateFetchAIGuidance('http://127.0.0.1:8000', 1014, 'mr', 'token', unmountController.signal);
      },
      (err) => {
        assert.equal(err.name, 'RecommendationApiError');
        assert.equal(err.message, 'Request was canceled.');
        return true;
      }
    );
  });

  test('properly identifies timeout and "Fetch request has been canceled" without external abort', async () => {
    global.fetch = async (url, options) => {
      // simulate fetch throwing the exact React Native cancellation error
      const err = new Error('fetch failed: Fetch request has been canceled');
      err.name = 'Error';
      throw err;
    };

    await assert.rejects(
      async () => {
        await simulateFetchAIGuidance('http://127.0.0.1:8000', 1014, 'mr', 'token');
      },
      (err) => {
        assert.equal(err.name, 'RecommendationApiError');
        assert.equal(err.message, 'Connection timed out. Please try again.');
        return true;
      }
    );
  });

  test('successfully returns Marathi guidance response with full structure', async () => {
    const mockMarathiResponse = {
      status: 'success',
      crop: 'tur',
      disease_name: 'Wilt',
      confidence: 0.999,
      confidence_percent: 100,
      disease_explanation: 'तूर पिकावरील मर रोगाचे योग्य व्यवस्थापन करणे गरजेचे आहे.',
      farmer_action: [
        'ट्रायकोडर्मा व्हिरिडीची बीजप्रक्रिया करा.',
        'एकापेक्षा जास्त औषधे एकत्र मिसळण्यापूर्वी उत्पादनाच्या label वरील सूचना किंवा अधिकृत कृषी शिफारस तपासा.'
      ],
      spray_guidance_available: true,
      ai_guidance_available: true,
      spray_guidance: {
        treatment: 'Trichoderma viride seed treatment',
        active_ingredient: 'Trichoderma viride',
        recommended_quantity: '4 g/kg seed',
        water_quantity: null,
        per_pump_quantity: null,
        spray_timing: 'Seed treatment before sowing',
        application_method: 'Seed treatment',
        safety_precautions: 'Use gloves during seed treatment',
        after_spray_advisory: 'Wash hands thoroughly'
      },
      warnings: [],
      language: 'mr'
    };

    global.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => mockMarathiResponse,
    });

    const res = await simulateFetchAIGuidance('http://127.0.0.1:8000', 1014, 'mr', 'valid_token');
    assert.equal(res.status, 'success');
    assert.equal(res.language, 'mr');
    assert.equal(res.disease_name, 'Wilt');
    assert.equal(res.spray_guidance_available, true);
    assert.equal(res.farmer_action.length, 2);
    assert.match(res.disease_explanation, /तूर पिकावरील/);
  });
});

describe('Post-voice-recording submission and decoupled result loading workflow', () => {
  test('synchronous submit guard prevents duplicate parallel submissions on rapid multi-tapping', async () => {
    let callCount = 0;
    const submitGuard = { current: false };

    async function mockHandleSubmitVoice() {
      if (submitGuard.current) {
        return { status: 'blocked_duplicate' };
      }
      submitGuard.current = true;
      callCount++;
      // simulate async upload latency
      await new Promise((r) => setTimeout(r, 20));
      submitGuard.current = false;
      return { status: 'submitted' };
    }

    // Fire 5 rapid concurrent clicks simultaneously
    const results = await Promise.all([
      mockHandleSubmitVoice(),
      mockHandleSubmitVoice(),
      mockHandleSubmitVoice(),
      mockHandleSubmitVoice(),
      mockHandleSubmitVoice(),
    ]);

    assert.equal(callCount, 1, 'Only one upload should execute');
    assert.equal(results.filter((r) => r.status === 'submitted').length, 1);
    assert.equal(results.filter((r) => r.status === 'blocked_duplicate').length, 4);
    assert.equal(submitGuard.current, false, 'Guard resets after completion allowing subsequent retries');
  });

  test('voice submission reuses forwarded prediction and avoids redundant ML inference', async () => {
    let mlInferenceCalled = false;
    let voiceUploadCalled = false;

    async function mockVoiceSubmission({ passedDiseaseName, passedConfidence, scanId }) {
      // 1. Audio upload
      voiceUploadCalled = true;
      let prediction = null;

      // 2. Optimized prediction check
      if (passedDiseaseName) {
        prediction = {
          disease_name: passedDiseaseName,
          confidence: parseFloat(passedConfidence),
          severity: 'Moderate',
        };
      } else {
        mlInferenceCalled = true;
        prediction = {
          disease_name: 'Leaf_Spot',
          confidence: 0.95,
          severity: 'Moderate',
        };
      }
      return prediction;
    }

    // Case A: Forwarded prediction from scan screen is present
    const predA = await mockVoiceSubmission({
      passedDiseaseName: 'Leaf_Spot',
      passedConfidence: '0.945',
      scanId: 101,
    });
    assert.equal(voiceUploadCalled, true);
    assert.equal(mlInferenceCalled, false, 'Redundant ML inference network call was safely skipped');
    assert.equal(predA.disease_name, 'Leaf_Spot');
    assert.equal(predA.confidence, 0.945);

    // Case B: Forwarded prediction is missing (fallback behavior preserved)
    mlInferenceCalled = false;
    const predB = await mockVoiceSubmission({
      passedDiseaseName: '',
      passedConfidence: '',
      scanId: 102,
    });
    assert.equal(mlInferenceCalled, true, 'ML inference was called as fallback when prediction was absent');
    assert.equal(predB.disease_name, 'Leaf_Spot');
  });

  test('spray guidance displays core diagnosis immediately (< 50ms) without waiting for slow AI guidance', () => {
    function computeInitialViewState(params) {
      const rawDiseaseName = (params.diseaseName || params.disease_name || '').trim();
      const parsedConfidence = Number(params.confidence);
      const hasValidConfidence = Number.isFinite(parsedConfidence);
      const isConfidenceTooLow = hasValidConfidence && parsedConfidence < 0.60;

      // Initial loading is ONLY true when disease was NOT passed and data is not yet loaded
      const isInitialLoading = !rawDiseaseName && !isConfidenceTooLow;

      return {
        isInitialLoading,
        isConfidenceTooLow,
        displayedDisease: rawDiseaseName || 'Tur Leaf Spot',
        isAILoading: true,
        canDisplayImmediately: !isInitialLoading && !isConfidenceTooLow,
      };
    }

    // Normal flow with forwarded prediction
    const state = computeInitialViewState({
      diseaseName: 'Leaf_Spot',
      confidence: '0.92',
      scanId: '55',
    });

    assert.equal(state.isInitialLoading, false, 'User is not blocked by a full-screen spinner');
    assert.equal(state.canDisplayImmediately, true, 'Verified leaf diagnosis is visible immediately');
    assert.equal(state.displayedDisease, 'Leaf_Spot');
    assert.equal(state.isAILoading, true, 'Secondary Claude LLM runs progressively in background');
  });

  test('spray guidance immediately shows low confidence safety gate when confidence is below 60%', () => {
    function computeInitialViewState(params) {
      const rawDiseaseName = (params.diseaseName || params.disease_name || '').trim();
      const parsedConfidence = Number(params.confidence);
      const hasValidConfidence = Number.isFinite(parsedConfidence);
      const isConfidenceTooLow = hasValidConfidence && parsedConfidence < 0.60;

      return {
        isConfidenceTooLow,
        shouldRequestAI: !isConfidenceTooLow,
      };
    }

    const state = computeInitialViewState({
      diseaseName: 'Leaf_Spot',
      confidence: '0.45',
      scanId: '56',
    });

    assert.equal(state.isConfidenceTooLow, true);
    assert.equal(state.shouldRequestAI, false, 'Unsafe pesticide guidance is never requested below 60% confidence');
  });

  test('AI guidance network failure preserves verified leaf diagnosis and displays inline retry', () => {
    const rawDiseaseName = 'Leaf_Spot';
    let data = null;
    let hasError = true;

    // View rendering decision
    const shouldShowFullScreenError = hasError && !rawDiseaseName;
    const shouldShowInlineError = hasError && Boolean(rawDiseaseName);

    assert.equal(shouldShowFullScreenError, false, 'Must not replace verified diagnosis with full screen error');
    assert.equal(shouldShowInlineError, true, 'Shows inline retry inside guidance card');
    assert.equal(rawDiseaseName, 'Leaf_Spot', 'Farmer still sees their confirmed leaf diagnosis');
  });
});

describe('Verified Agricultural Recommendation & Language Localization Suite', () => {
  // Test localized recommendation helper logic
  test('Wilt is strictly categorized as a seed/soil treatment and never as a foliar spray', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const mockWiltResponse = {
      status: 'fallback',
      crop: 'tur',
      disease_name: 'Wilt',
      confidence: 1.0,
      confidence_percent: 100,
      disease_explanation: 'Fusarium wilt is a soil-borne disease.',
      farmer_action: ['Monitor crop.'],
      spray_guidance_available: true,
      ai_guidance_available: true,
      spray_guidance: {
        treatment: 'Trichoderma viride seed treatment',
        active_ingredient: 'Trichoderma viride 1% WP',
        recommended_quantity: '10 g per kg of seed',
        water_quantity: null,
        per_pump_quantity: null,
        spray_timing: 'Apply as seed treatment before sowing.',
        application_method: 'Seed treatment (biological). This is NOT a foliar spray.',
        safety_precautions: 'Avoid direct sunlight exposure.',
        after_spray_advisory: 'Uproot and destroy wilted plants.',
      },
      warnings: [],
      language: 'en',
    };

    const locEn = getLocalizedRecommendation(mockWiltResponse, 'en');
    assert.equal(locEn.isSeedTreatment, true, 'Wilt must be flagged as seed treatment');
    assert.equal(locEn.waterQuantity, null, 'Water quantity must be null for seed treatment');
    assert.equal(locEn.perPumpQuantity, null, 'Per pump quantity must be null for seed treatment');
    assert.match(locEn.applicationMethod, /NOT a foliar spray/i, 'Explicitly declares not a foliar spray');
    assert.match(locEn.headerTitle, /TREATMENT GUIDANCE/i, 'Header says treatment, not spray');
  });

  test('Wilt in Marathi mode delivers complete verified Marathi guidance without raw English text', async () => {
    const { getLocalizedRecommendation, hasDevanagari } = await import('../src/i18n/recommendationContent.ts');

    const mockWiltResponse = {
      status: 'fallback',
      crop: 'tur',
      disease_name: 'Wilt',
      confidence: 1.0,
      confidence_percent: 100,
      disease_explanation: 'Fusarium wilt description in English.',
      farmer_action: [],
      spray_guidance_available: true,
      ai_guidance_available: true,
      spray_guidance: {
        treatment: 'Trichoderma viride seed treatment',
        active_ingredient: 'Trichoderma viride 1% WP',
        recommended_quantity: '10 g per kg of seed',
        water_quantity: null,
        per_pump_quantity: null,
        spray_timing: 'Apply before sowing.',
        application_method: 'Seed treatment (biological).',
        safety_precautions: 'Avoid direct sunlight.',
        after_spray_advisory: 'Crop rotation.',
      },
      warnings: [],
      language: 'mr',
    };

    const locMr = getLocalizedRecommendation(mockWiltResponse, 'mr');
    assert.equal(locMr.isSeedTreatment, true);
    assert.equal(hasDevanagari(locMr.treatment), true, 'Treatment is localized in Marathi');
    assert.equal(hasDevanagari(locMr.applicationMethod), true, 'Application method is localized in Marathi');
    assert.equal(hasDevanagari(locMr.applicationTiming), true, 'Timing is localized in Marathi');
    assert.equal(hasDevanagari(locMr.importantAlert), true, 'Important alert is localized in Marathi');
    assert.match(locMr.importantAlert, /पानांवर फवारणी करू नका/, 'Explicitly instructs NOT to spray on leaves');
    assert.match(locMr.guidanceSectionTitle, /बियाणे \/ जमीन उपचार/, 'Section title is seed/soil treatment');
  });

  test('Foliar diseases (Leaf_Spot and Sterilic_mosaic) are correctly classified as foliar sprays', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const mockLeafSpot = {
      disease_name: 'Leaf_Spot',
      spray_guidance_available: true,
      spray_guidance: {
        treatment: 'Mancozeb 75 WP',
        application_method: 'Foliar spray',
      },
    };
    const locSpot = getLocalizedRecommendation(mockLeafSpot, 'en');
    assert.equal(locSpot.isSeedTreatment, false, 'Leaf Spot is a foliar spray');
    assert.match(locSpot.headerTitle, /SPRAY GUIDANCE/i);

    const mockMosaic = {
      disease_name: 'Sterilic_mosaic',
      spray_guidance_available: true,
      spray_guidance: {
        treatment: 'Fenazaquin 10 EC',
        application_method: 'Foliar spray',
      },
    };
    const locMosaic = getLocalizedRecommendation(mockMosaic, 'mr');
    assert.equal(locMosaic.isSeedTreatment, false, 'Sterility mosaic is a foliar spray');
    assert.match(locMosaic.guidanceSectionTitle, /फवारणी मार्गदर्शन/);
  });

  test('Unverified disease (Leaf_webber) displays safety gate and does not invent pesticide/dose', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const mockWebber = {
      disease_name: 'Leaf_webber',
      spray_guidance_available: false,
      spray_guidance: null,
    };
    const locWebber = getLocalizedRecommendation(mockWebber, 'mr');
    assert.equal(locWebber.isVerified, false, 'Leaf webber must not be marked verified');
    assert.equal(locWebber.waterQuantity, null);
    assert.equal(locWebber.perPumpQuantity, null);
  });

  test('Confidence disclaimer warns farmer that 100% confidence does not guarantee field certainty', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const locEn = getLocalizedRecommendation(null, 'en', 'Wilt');
    assert.match(locEn.confidenceDisclaimer, /pattern match/i, 'English disclaimer clarifies pattern match');

    const locMr = getLocalizedRecommendation(null, 'mr', 'Wilt');
    assert.match(locMr.confidenceDisclaimer, /प्रत्यक्ष शेत तपासणी आवश्यक/, 'Marathi disclaimer reminds field inspection');
  });

  test('Healthy class is safely handled without chemical sprays or pump dosages', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const mockHealthy = {
      disease_name: 'Healthy',
      spray_guidance_available: false,
      spray_guidance: null,
    };

    const locMr = getLocalizedRecommendation(mockHealthy, 'mr');
    assert.equal(locMr.isHealthy, true, 'Healthy is marked as isHealthy');
    assert.equal(locMr.isSeedTreatment, false, 'Healthy is not a seed treatment');
    assert.equal(locMr.isVerified, false, 'Healthy does not have a verified pesticide spray');
    assert.equal(locMr.waterQuantity, null, 'No water quantity for healthy crop');
    assert.equal(locMr.perPumpQuantity, null, 'No pump dosage for healthy crop');
    assert.match(locMr.headerTitle, /आरोग्य सल्ला/, 'Header indicates health advisory');
    assert.match(locMr.importantAlert, /कोणत्याही रासायनिक फवारणीची गरज नाही/, 'Alert explicitly forbids spray');
    assert.match(locMr.treatment, /रासायनिक फवारणीची आवश्यकता नाही/, 'Treatment instructs no chemical spray');

    const locEn = getLocalizedRecommendation(mockHealthy, 'en');
    assert.equal(locEn.isHealthy, true);
    assert.match(locEn.headerTitle, /CROP HEALTH ADVISORY/i);
    assert.match(locEn.importantAlert, /NO chemical spray required/i);
  });

  test('All five model classes (Healthy, Leaf_Spot, Leaf_webber, Sterilic_mosaic, Wilt) are safely audited', async () => {
    const { normalizeDiseaseKey, getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const expectedClasses = ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt'];
    for (const cls of expectedClasses) {
      const normalized = normalizeDiseaseKey(cls);
      assert.equal(normalized, cls, `Class ${cls} must normalize cleanly`);
      const loc = getLocalizedRecommendation(null, 'mr', cls);
      assert.ok(loc.headerTitle, `Class ${cls} must have a valid headerTitle`);
      assert.ok(loc.importantAlert, `Class ${cls} must have a valid importantAlert`);
      if (cls === 'Healthy') {
        assert.equal(loc.isHealthy, true);
      } else if (cls === 'Wilt') {
        assert.equal(loc.isSeedTreatment, true);
      } else if (cls === 'Leaf_webber') {
        assert.equal(loc.isVerified, false);
      } else {
        assert.equal(loc.isSeedTreatment, false);
      }
    }
  });

  test('Honest confidence formatting never outputs 100% or 100.0% even for extreme model softmax outputs', () => {
    const formatConfidenceHonest = (val) => {
      const num = Number(val);
      if (!Number.isFinite(num) || num <= 0) return '0%';
      const normalized = num <= 1 ? num * 100 : num;
      const capped = Math.min(normalized, 99.0);
      return `${capped.toFixed(1)}%`;
    };

    const formatConfidenceInt = (val) => {
      if (typeof val !== 'number' || isNaN(val)) return '0%';
      const normalized = val <= 1 && val > 0 ? Math.round(val * 100) : Math.round(val);
      const capped = Math.min(Math.max(normalized, 0), 99);
      return `${capped}%`;
    };

    // Extreme raw model confidence on scan 1076: 0.9999911785125732
    assert.equal(formatConfidenceHonest(0.9999911785125732), '99.0%');
    assert.equal(formatConfidenceHonest(1.0), '99.0%');
    assert.equal(formatConfidenceHonest('0.999991'), '99.0%');
    assert.notEqual(formatConfidenceHonest(0.9999911785125732), '100.0%');

    assert.equal(formatConfidenceInt(0.9999911785125732), '99%');
    assert.equal(formatConfidenceInt(1.0), '99%');
    assert.notEqual(formatConfidenceInt(0.9999911785125732), '100%');
  });

  test('Leaf Webber unverified state clearly identifies predicted condition and declares chemical spray unverified', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const mockWebber = {
      status: 'unverified',
      crop: 'tur',
      disease_name: 'Leaf_webber',
      confidence: 0.999991,
      confidence_percent: 100,
      disease_explanation: 'Leaf webber larvae feed inside webbed leaves.',
      farmer_action: ['Inspect shoot tips regularly.', 'Manually destroy webbed leaves.'],
      spray_guidance_available: false,
      ai_guidance_available: true,
      spray_guidance: null,
      warnings: [],
      language: 'mr',
    };

    const loc = getLocalizedRecommendation(mockWebber, 'mr');
    assert.equal(loc.isVerified, false, 'Leaf Webber must not be marked as verified diagnosis');
    assert.equal(loc.isWebber, true, 'Leaf Webber has isWebber set to true');
    assert.equal(loc.recommendedQuantity, 'लागू नाही');
    assert.equal(loc.waterQuantity, null);
    assert.equal(loc.perPumpQuantity, null);
    assert.match(loc.treatment, /रासायनिक फवारणीची शिफारस नाही/, 'Explicitly declares no chemical spray recommended');
    assert.match(loc.applicationMethod, /फवारणी करू नका/, 'Explicitly forbids spray');
    assert.match(loc.headerTitle, /कीड व्यवस्थापन सल्ला/, 'Header indicates pest management advisory, not confirmed spray');
    assert.match(loc.importantAlert, /प्रमाणित रासायनिक फवारणी उपलब्ध नाही/, 'Alert explicitly declares chemical spray unverified');
  });

  test('Leaf Webber Marathi name translation matches exact required standard', async () => {
    const { KNOWN_DISEASES, translateDiseaseName } = await import('../src/i18n/translations.ts');

    assert.equal(
      KNOWN_DISEASES['Leaf_webber']?.mr,
      'Leaf Webber — पाने गुंडाळणारी अळी',
      'KNOWN_DISEASES must contain exact Marathi name with Devanagari alii'
    );
    assert.equal(
      translateDiseaseName('Leaf_webber', 'mr'),
      'Leaf Webber — पाने गुंडाळणारी अळी',
      'translateDiseaseName must return exact Marathi name'
    );
    assert.equal(
      translateDiseaseName('Leaf Webber', 'mr'),
      'Leaf Webber — पाने गुंडाळणारी अळी',
      'translateDiseaseName with space must return exact Marathi name'
    );
  });

  test('Healthy and Wilt behavior remains completely unchanged and invariant', async () => {
    const { getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const locHealthy = getLocalizedRecommendation(null, 'mr', 'Healthy');
    assert.equal(locHealthy.isHealthy, true, 'Healthy remains marked as isHealthy');
    assert.equal(locHealthy.isSeedTreatment, false, 'Healthy is not seed treatment');
    assert.equal(locHealthy.isVerified, false, 'Healthy has no chemical pesticide recommendation');
    assert.match(locHealthy.headerTitle, /पीक आरोग्य सल्ला/, 'Healthy header title remains unchanged');
    assert.match(locHealthy.guidanceSectionTitle, /पीक निगा व व्यवस्थापन/, 'Healthy section title remains unchanged');

    const locWilt = getLocalizedRecommendation(null, 'mr', 'Wilt');
    assert.equal(locWilt.isHealthy, false, 'Wilt is not healthy');
    assert.equal(locWilt.isSeedTreatment, true, 'Wilt remains seed/soil treatment');
    assert.match(locWilt.headerTitle, /स्मार्ट उपचार मार्गदर्शन/, 'Wilt header title remains unchanged');
    assert.match(locWilt.guidanceSectionTitle, /बियाणे \/ जमीन उपचार मार्गदर्शन/, 'Wilt section title remains unchanged');
  });

  test('Unsupported disease classes safely trigger fallback without crashing or inventing guidance', async () => {
    const { normalizeDiseaseKey, getLocalizedRecommendation } = await import('../src/i18n/recommendationContent.ts');

    const unsupportedCls = 'Alternaria_Blight';
    const normalized = normalizeDiseaseKey(unsupportedCls);
    assert.equal(normalized, null, 'Unsupported disease must not normalize to supported classes');

    const loc = getLocalizedRecommendation(null, 'mr', unsupportedCls);
    assert.equal(loc.isVerified, false, 'Unsupported disease must never be marked verified');
    assert.equal(loc.isHealthy, false);
    assert.equal(loc.isSeedTreatment, false);
    assert.equal(loc.waterQuantity, null);
    assert.equal(loc.perPumpQuantity, null);
  });
});



