import { useMemo, useRef } from 'react';
import './Message.css';

function Message({ role, content, isStreaming }) {
  const lastImageHtmlRef = useRef('');

  // 提取圖片 HTML，並在 streaming 時保持穩定
  const { textHtml, imageHtml } = useMemo(() => {
    const result = extractImagesFromContent(content);
    // 如果有新圖片，更新緩存
    if (result.imageHtml) {
      lastImageHtmlRef.current = result.imageHtml;
    }
    return {
      textHtml: result.textHtml,
      // 使用緩存的圖片 HTML，避免 streaming 時閃爍
      imageHtml: lastImageHtmlRef.current
    };
  }, [content]);

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <div className="message-role">{role === 'user' ? 'You' : 'Assistant'}</div>
        <div className="message-text">
          {/* 文字內容 - 可以隨 stream 更新 */}
          <div dangerouslySetInnerHTML={{ __html: textHtml }} />
          {/* 圖片區域 - 獨立渲染，避免閃爍 */}
          {imageHtml && (
            <div
              className="images-section"
              dangerouslySetInnerHTML={{ __html: imageHtml }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function extractImagesFromContent(content) {
  if (!content) return { textHtml: '', imageHtml: '' };

  let html = content;
  let imageHtml = '';
  const foundImages = new Set();

  // 先統一路徑分隔符號（Windows 反斜線轉正斜線）
  html = html.replace(/\\/g, '/');

  // Helper function to add image
  const addImage = (imgSrc, altText = 'Generated Image') => {
    if (!foundImages.has(imgSrc)) {
      foundImages.add(imgSrc);
      imageHtml += `<div class="generated-image-container">
        <img src="${imgSrc}" alt="${altText}" class="generated-image" loading="lazy" />
        <a href="${imgSrc}" target="_blank" rel="noopener" class="image-link">🔗 View Full Size</a>
      </div>`;
    }
  };

  // 1. 處理 Markdown 圖片連結: [text](path/to/image.png)
  // 匹配包含圖片副檔名的 Markdown 連結
  const markdownLinkWithImageRegex = /\[([^\]]*)\]\(([^)]*?(?:z-image[^)]*|[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)))\)/gi;
  html = html.replace(markdownLinkWithImageRegex, (match, text, url) => {
    // 從 URL 提取檔名
    let imgSrc = url;

    // 處理 sandbox 路徑
    if (url.includes('sandbox:')) {
      const filename = url.match(/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)$/i);
      if (filename) {
        imgSrc = `/images/${filename[0]}`;
      }
    }
    // 處理 /mnt/data/ 路徑
    else if (url.includes('/mnt/data/')) {
      const filename = url.match(/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)$/i);
      if (filename) {
        imgSrc = `/images/${filename[0]}`;
      }
    }
    // 處理 outputs/images/ 路徑
    else if (url.includes('outputs/images/')) {
      imgSrc = url.replace(/.*outputs\/images\//, '/images/');
    }
    // 檢查是否是圖片檔案
    else if (/\.(png|jpg|jpeg|webp|gif)$/i.test(url)) {
      const filename = url.match(/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)$/i);
      if (filename) {
        imgSrc = `/images/${filename[0]}`;
      }
    }

    addImage(imgSrc, text || 'Generated Image');
    return ''; // 移除原始 markdown 連結
  });

  // 2. 處理 outputs/images/xxx.png 格式的路徑
  const outputsPathRegex = /(?:(?:Path|saved as|saved to|Generated image)[:\s]+)?(outputs\/images\/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif))/gi;
  html = html.replace(outputsPathRegex, (match, path) => {
    const imgSrc = '/' + path.replace('outputs/', '');
    addImage(imgSrc);
    return '';
  });

  // 3. 處理直接的 /images/xxx.png 路徑
  const directImageRegex = /(?<!src="|href=")(\/images\/[\w\-_.]+\.(?:png|jpg|jpeg|webp|gif))/gi;
  html = html.replace(directImageRegex, (match, path) => {
    addImage(path);
    return '';
  });

  // 4. 處理獨立的圖片檔名 (z-image_xxxxx_.png)
  const standaloneImageRegex = /(?<![\/\w])(z-image[\w\-_.]*\.(?:png|jpg|jpeg|webp|gif))(?![\/\w])/gi;
  html = html.replace(standaloneImageRegex, (match, filename) => {
    addImage(`/images/${filename}`);
    return '';
  });

  // 簡單的 Markdown 轉換
  const textHtml = html
    // 程式碼區塊
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 行內程式碼
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 粗體
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜體
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 一般連結（非圖片）
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
      // 如果是圖片連結，不處理（已經處理過）
      if (/\.(png|jpg|jpeg|webp|gif)$/i.test(url)) {
        return '';
      }
      return `<a href="${url}" target="_blank" rel="noopener">${text}</a>`;
    })
    // 換行
    .replace(/\n/g, '<br>')
    // 清理多餘的空白行
    .replace(/(<br>){3,}/g, '<br><br>');

  return { textHtml, imageHtml };
}

export default Message;
