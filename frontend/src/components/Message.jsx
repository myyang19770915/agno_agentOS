import './Message.css';

function Message({ role, content }) {
  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <div className="message-role">{role === 'user' ? 'You' : 'Assistant'}</div>
        <div className="message-text" dangerouslySetInnerHTML={{
          __html: formatContent(content)
        }} />
      </div>
    </div>
  );
}

function formatContent(content) {
  if (!content) return '';

  let html = content;

  // 先統一路徑分隔符號（Windows 反斜線轉正斜線）
  html = html.replace(/\\/g, '/');

  // 檢測並渲染圖片路徑
  // 支援格式：
  // - outputs/images/xxx.png
  // - /images/xxx.png
  // - Path: outputs/images/xxx.png
  // - saved as: outputs/images/xxx.png
  const imagePathRegex = /(?:(?:Path|saved as)[:\s]+)?(outputs\/images\/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif))/gi;

  html = html.replace(imagePathRegex, (match, path) => {
    // 將 outputs/images/ 轉換為 /images/ 供前端存取
    const imgSrc = '/' + path.replace('outputs/', '');
    return `<div class="generated-image-container">
      <img src="${imgSrc}" alt="Generated Image" class="generated-image" loading="lazy" />
      <a href="${imgSrc}" target="_blank" rel="noopener" class="image-link">🔗 View Full Size</a>
    </div>`;
  });

  // 也處理直接以 /images/ 開頭的路徑
  const directImageRegex = /(?<!src="|href=")(\/images\/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif))/gi;
  html = html.replace(directImageRegex, (match, path) => {
    return `<div class="generated-image-container">
      <img src="${path}" alt="Generated Image" class="generated-image" loading="lazy" />
      <a href="${path}" target="_blank" rel="noopener" class="image-link">🔗 View Full Size</a>
    </div>`;
  });

  // 簡單的 Markdown 轉換
  html = html
    // 程式碼區塊
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 行內程式碼
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 粗體
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜體
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 連結（但不處理已經是 img 或 a 標籤內的）
    .replace(/(?<!["=])\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // 換行
    .replace(/\n/g, '<br>');

  return html;
}

export default Message;
