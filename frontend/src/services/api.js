import axios from 'axios';

const client = axios.create({ baseURL: '/api' });

/**
 * @typedef {Object} CategoryNode
 * @property {number} id
 * @property {string} name
 * @property {number|null} parent_id
 * @property {CategoryNode[]} children
 */

/**
 * @typedef {Object} WorkRecord
 * @property {number} category_id
 * @property {number} work_time
 * @property {string} recorded_at
 */

/**
 * @typedef {Object} TrendResult
 * @property {number} slope
 * @property {number} intercept
 * @property {boolean} is_warning
 */

/**
 * @typedef {Object} AnomalyResult
 * @property {string} recorded_at
 * @property {number} anomaly_score
 */

/**
 * @typedef {Object} AnalysisResult
 * @property {TrendResult|null} trend
 * @property {AnomalyResult[]} anomalies
 */

/**
 * @typedef {Object} BaselineConfig
 * @property {string} baseline_start
 * @property {string} baseline_end
 * @property {number} sensitivity
 * @property {string[]} excluded_points
 */

/**
 * GET /api/categories
 * @param {number} [rootId] - ルートカテゴリID（省略時は全ツリー）
 * @returns {Promise<CategoryNode[]>}
 */
export async function fetchCategories(rootId) {
  const params = {};
  if (rootId != null) params.root = rootId;
  const { data } = await client.get('/categories', { params });
  return data.categories;
}

/**
 * GET /api/records?category_id=...&start=...&end=...
 * @param {number} categoryId
 * @param {string} [start] - ISO 8601 datetime
 * @param {string} [end]   - ISO 8601 datetime
 * @returns {Promise<WorkRecord[]>}
 */
export async function fetchRecords(categoryId, start, end) {
  const params = { category_id: categoryId };
  if (start) params.start = start;
  if (end) params.end = end;
  const { data } = await client.get('/records', { params });
  return data.records;
}

/**
 * GET /api/results/{category_id}
 * @param {number} categoryId
 * @returns {Promise<AnalysisResult>}
 */
export async function fetchResults(categoryId) {
  const { data } = await client.get(`/results/${categoryId}`);
  return data;
}

/**
 * GET /api/models/{category_id}
 * @param {number} categoryId
 * @returns {Promise<BaselineConfig>}
 */
export async function fetchBaselineConfig(categoryId) {
  const { data } = await client.get(`/models/${categoryId}`);
  return data;
}

/**
 * PUT /api/models/{category_id}
 * @param {number} categoryId
 * @param {Object} config
 * @param {string} config.baseline_start
 * @param {string} config.baseline_end
 * @param {number} config.sensitivity
 * @param {string[]} [config.excluded_points]
 * @returns {Promise<{retrained: boolean}>}
 */
export async function saveBaselineConfig(categoryId, config) {
  const { data } = await client.put(`/models/${categoryId}`, config);
  return data;
}

/**
 * DELETE /api/models/{category_id}
 * @param {number} categoryId
 * @returns {Promise<{deleted: boolean}>}
 */
export async function deleteBaselineConfig(categoryId) {
  const { data } = await client.delete(`/models/${categoryId}`);
  return data;
}

/**
 * POST /api/analysis/run
 * @returns {Promise<{processed_categories: number}>}
 */
export async function triggerAnalysis() {
  const { data } = await client.post('/analysis/run');
  return data;
}
