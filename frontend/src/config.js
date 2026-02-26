/**
 * 全域設定 — 部署路徑與 API 基底
 *
 * 後端 root_path: /agentapi   (反向代理 prefix)
 * 前端 base:      /agentplatform
 *
 * 前端 API 請求統一走 /agentplatform/api，
 * 確保透過 Nginx 反向代理（/agentplatform/ → Vite）時也能正確轉發到後端。
 */

// 後端 API 基底路徑（走前端 base 下的子路徑，Vite proxy 或 Nginx sub-location 轉發到後端）
export const API_BASE = '/agentplatform/api';

// 後端靜態資源路徑
export const IMAGES_BASE = `${API_BASE}/images`;
export const CHARTS_BASE = `${API_BASE}/charts`;
export const DOWNLOADS_BASE = `${API_BASE}/downloads`;
export const DOWNLOAD_BASE = `${API_BASE}/download`;
