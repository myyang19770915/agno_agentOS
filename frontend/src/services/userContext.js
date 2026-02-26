/**
 * 使用者身份管理模組
 *
 * 透過 postMessage 向父視窗請求使用者資訊 (emplid / email)。
 * 若超過指定時間未收到回應，自動使用 "unknown" 作為預設值，
 * 避免阻塞 UI 運作。
 */

const DEFAULT_TIMEOUT_MS = 5000; // 5 秒逾時
const FALLBACK_USER_ID = 'unknown';

let _userId = null;
let _email = null;
let _resolved = false;
let _promise = null;
let _listeners = [];

/**
 * 初始化使用者資訊擷取流程。
 * 呼叫一次即可，重複呼叫會回傳同一個 Promise。
 * @param {number} timeoutMs - 逾時毫秒數 (預設 5000)
 * @returns {Promise<string>} 解析後的 userId (emplid)
 */
export function initUser(timeoutMs = DEFAULT_TIMEOUT_MS) {
  if (_promise) return _promise;

  _promise = new Promise((resolve) => {
    // 監聽父視窗回應
    const handler = (event) => {
      if (event.data?.type === 'user-info') {
        const emplid = event.data.emplid || FALLBACK_USER_ID;
        const email = event.data.email || '';
        _setUser(emplid, email);
        window.removeEventListener('message', handler);
        clearTimeout(timer);
        resolve(emplid);
      }
    };

    window.addEventListener('message', handler);

    // 向父視窗請求使用者資訊
    try {
      window.parent.postMessage({ type: 'get-user' }, '*');
    } catch (e) {
      console.warn('[UserContext] postMessage to parent failed:', e);
    }

    // 逾時 fallback
    const timer = setTimeout(() => {
      if (!_resolved) {
        console.warn(`[UserContext] 未在 ${timeoutMs}ms 內收到 user-info，使用預設值 "${FALLBACK_USER_ID}"`);
        window.removeEventListener('message', handler);
        _setUser(FALLBACK_USER_ID, '');
        resolve(FALLBACK_USER_ID);
      }
    }, timeoutMs);
  });

  return _promise;
}

function _setUser(userId, email) {
  _userId = userId;
  _email = email;
  _resolved = true;
  // 通知所有訂閱者
  _listeners.forEach(fn => fn(userId, email));
  _listeners = [];
}

/**
 * 取得目前的 userId (emplid)。
 * 若尚未解析完成，回傳 null。
 * @returns {string|null}
 */
export function getUserId() {
  return _userId;
}

/**
 * 取得目前的 email。
 * @returns {string|null}
 */
export function getUserEmail() {
  return _email;
}

/**
 * 是否已取得使用者資訊（含 fallback）。
 * @returns {boolean}
 */
export function isUserResolved() {
  return _resolved;
}

/**
 * 訂閱使用者資訊就緒事件。若已就緒則立即回呼。
 * @param {function} callback - (userId, email) => void
 */
export function onUserReady(callback) {
  if (_resolved) {
    callback(_userId, _email);
  } else {
    _listeners.push(callback);
  }
}
