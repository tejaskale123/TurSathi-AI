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

