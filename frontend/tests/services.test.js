import test from 'node:test';
import assert from 'node:assert/strict';
import { scanService } from '../src/services/scanService.js';
import { recommendationService } from '../src/services/recommendationService.js';

test('scanService: builds correct query parameters for scan history', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/scans\/\?skip=10&limit=20$/);
      return {
        ok: true,
        status: 200,
        headers: {
          get: () => 'application/json',
        },
        json: async () => ({
          total: 1,
          items: [{ id: 5, disease_detected: 'Fusarium Wilt' }],
        }),
      };
    };

    const res = await scanService.getScanHistory({ skip: 10, limit: 20 });
    assert.equal(res.total, 1);
    assert.equal(res.items[0].disease_detected, 'Fusarium Wilt');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('scanService: runPrediction calls POST /predictions/tur-leaf/:scanId', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/predictions\/tur-leaf\/142$/);
      assert.equal(options.method, 'POST');
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          scan_id: 142,
          crop: 'tur',
          status: 'completed',
          disease_name: 'Sterility Mosaic Disease',
          confidence: 0.89,
          severity: 'Moderate',
        }),
      };
    };

    const res = await scanService.runPrediction(142);
    assert.equal(res.scan_id, 142);
    assert.equal(res.disease_name, 'Sterility Mosaic Disease');
    assert.equal(res.confidence, 0.89);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('scanService: getAiGuidance calls POST /predictions/tur-leaf/:scanId/ai-guidance with language param', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/predictions\/tur-leaf\/142\/ai-guidance\?language=mr$/);
      assert.equal(options.method, 'POST');
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          status: 'success',
          crop: 'tur',
          disease_name: 'Sterility Mosaic Disease',
          disease_explanation: 'वांझ रोग (Sterility Mosaic Disease) हा विषाणूजन्य रोग आहे.',
          farmer_action: ['रोगट झाडे उपटून नष्ट करा.'],
        }),
      };
    };

    const res = await scanService.getAiGuidance(142, 'mr');
    assert.equal(res.status, 'success');
    assert.match(res.disease_explanation, /वांझ रोग/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('scanService: validateFrame sends FormData to /scans/validate-frame', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/scans\/validate-frame$/);
      assert.equal(options.method, 'POST');
      assert.ok(options.body instanceof FormData);
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          is_valid_tur: true,
          label: 'Pigeonpea Leaf',
          confidence: 0.94,
          message: 'Valid Tur leaf detected.',
        }),
      };
    };

    const blob = new Blob(['mock-image-bytes'], { type: 'image/jpeg' });
    const res = await scanService.validateFrame(blob);
    assert.equal(res.is_valid_tur, true);
    assert.equal(res.label, 'Pigeonpea Leaf');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('scanService: session tracking records and retrieves recent scans', () => {
  const mockScan = {
    scan_id: 888,
    crop: 'tur',
    disease_name: 'Phytophthora Blight',
    confidence: 0.91,
    severity: 'Severe',
    status: 'completed',
  };

  scanService.recordRecentScan(mockScan);
  const recents = scanService.getRecentScans();
  assert.ok(Array.isArray(recents));
  const found = recents.find((s) => s.scan_id === 888);
  assert.ok(found);
  assert.equal(found.disease_name, 'Phytophthora Blight');
});

test('recommendationService: passes correct disease class to recommendation endpoint', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/recommendations\/tur\/Fusarium%20Wilt(\/spray-guidance)?$/);
      return {
        ok: true,
        status: 200,
        headers: {
          get: () => 'application/json',
        },
        json: async () => ({
          disease_name: 'Fusarium Wilt',
          recommended_treatment: 'Apply Trichoderma viride',
          is_active: true,
        }),
      };
    };

    const rec = await recommendationService.getRecommendation('Fusarium Wilt');
    assert.equal(rec.disease_name, 'Fusarium Wilt');
    assert.equal(rec.is_active, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('recommendationService: getTurSprayGuidance fetches verified university guidance', async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/recommendations\/tur\/Fusarium%20Wilt\/spray-guidance$/);
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          crop: 'tur',
          disease_name: 'Fusarium Wilt',
          leaf_condition: 'Needs Treatment',
          important_alert: 'Avoid waterlogging in root zone',
          spray_guidance: ['Drench soil around plants with Carbendazim 1g/L'],
          after_spraying: ['Monitor plants for 7 days'],
          safety_precautions: ['Wear gloves and mask'],
          farmer_action: 'Treat affected patch immediately',
        }),
      };
    };

    const res = await recommendationService.getTurSprayGuidance('Fusarium Wilt');
    assert.equal(res.crop, 'tur');
    assert.equal(res.disease_name, 'Fusarium Wilt');
    assert.equal(res.spray_guidance.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
