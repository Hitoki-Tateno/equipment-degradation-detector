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
