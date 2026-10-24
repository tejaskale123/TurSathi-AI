/**
 * TurSathi AI — Disease Recommendations Service
 * 
 * Interacts with FastAPI recommendations and AI spray guidance:
 * - GET  /api/v1/recommendations/tur/{disease_name}/spray-guidance
 */

import { apiFetch } from '../config/api.js';

/**
 * Retrieves official verified agricultural spray guidance for a Tur disease.
 * Calls FastAPI GET /recommendations/tur/{disease_name}/spray-guidance
 *
 * @param {string} diseaseName - Disease name (e.g. "Fusarium Wilt", "Sterility Mosaic Disease", "Healthy")
 * @returns {Promise<{
 *   crop: string,
 *   disease_name: string,
 *   leaf_condition: string,
 *   important_alert: string,
 *   spray_guidance: Array<string>,
 *   after_spraying: Array<string>,
 *   safety_precautions: Array<string>,
 *   farmer_action: string
 * }>}
 */
export async function getTurSprayGuidance(diseaseName) {
  const cleanName = (diseaseName || '').trim();
  const encodedName = encodeURIComponent(cleanName);

  try {
    return await apiFetch(`/recommendations/tur/${encodedName}/spray-guidance`, {
      method: 'GET',
      requiresAuth: true,
    });
  } catch (err) {
    // If endpoint returns 404, try legacy path /recommendations/tur/{disease}
    if (err.status === 404) {
      return await apiFetch(`/recommendations/tur/${encodedName}`, {
        method: 'GET',
        requiresAuth: true,
      });
    }
    throw err;
  }
}

/**
 * Compatibility alias for getTurSprayGuidance
 *
 * @param {string} diseaseName
 * @returns {Promise<any>}
 */
export async function getRecommendation(diseaseName) {
  return getTurSprayGuidance(diseaseName);
}

/**
 * Generates personalized spray guidance.
 *
 * @param {{ disease_name: string } | string} payload
 * @param {string} [language="mr"]
 * @returns {Promise<any>}
 */
export async function getSprayGuidance(payload, language = 'mr') {
  const diseaseName = typeof payload === 'string' ? payload : payload?.disease_name;
  return getTurSprayGuidance(diseaseName);
}

export const recommendationService = {
  getTurSprayGuidance,
  getRecommendation,
  getSprayGuidance,
};

export default recommendationService;
