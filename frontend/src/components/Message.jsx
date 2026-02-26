import { memo, useMemo, useRef, useEffect } from 'react';
import { API_BASE, IMAGES_BASE, CHARTS_BASE, DOWNLOADS_BASE } from '../config';
import './Message.css';

/**
 * 獨立的圖表區塊元件 — 只有 chartHtml 變化時才重新渲染，
 * 避免父元件（Message）重新渲染時 iframe 被瀏覽器 re-paint / 閃爍。
 */
const ChartSection = memo(function ChartSection({ html }) {
  if (!html) return null;
  return (
    <div
      className="charts-section"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
});

const Message = memo(function Message({ role, content, isStreaming }) {
  const lastImageHtmlRef = useRef('');
  const lastChartHtmlRef = useRef('');
  const lastDownloadHtmlRef = useRef('');
  const messageTextRef = useRef(null);

  // 提取圖片/圖表/下載 HTML，並在 streaming 時保持穩定
  const { textHtml, imageHtml, chartHtml, downloadHtml } = useMemo(() => {
    const result = extractImagesFromContent(content);
    if (result.imageHtml) lastImageHtmlRef.current = result.imageHtml;
    if (result.chartHtml) lastChartHtmlRef.current = result.chartHtml;
    if (result.downloadHtml) lastDownloadHtmlRef.current = result.downloadHtml;
    return {
      textHtml: result.textHtml,
      imageHtml: lastImageHtmlRef.current,
      chartHtml: lastChartHtmlRef.current,
      downloadHtml: lastDownloadHtmlRef.current,
    };
  }, [content]);

  // 攔截下載按鈕與圖片錯誤，避免跳離對話頁面
  useEffect(() => {
    const container = messageTextRef.current;
    if (!container) return;

    // 下載按鈕：先 HEAD 確認檔案存在才下載，否則跳出警告
    const handleDownloadClick = async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const link = e.currentTarget;
      const url = link.href;
      const filename = link.getAttribute('download') || url.split('/').pop();
      try {
        const res = await fetch(url, { method: 'HEAD' });
        if (res.ok) {
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        } else {
          alert(`⚠️ 檔案不存在或尚未生成\n\n${url}\n\n請確認 Agent 是否已完成檔案生成。`);
        }
      } catch {
        alert(`⚠️ 無法連線到伺服器\n\n請確認後端服務 (port 8013) 是否正在運行。`);
      }
    };

    // 圖片 404：替換為錯誤提示，不顯示破圖
    const handleImageError = (e) => {
      const img = e.currentTarget;
      img.removeEventListener('error', handleImageError);
      const wrapper = img.closest('.generated-image-container');
      if (wrapper) {
        const src = img.src;
        wrapper.innerHTML = `<div class="image-error">⚠️ 圖片不存在或載入失敗<br/><small>${src}</small></div>`;
      }
    };

    const downloadLinks = container.querySelectorAll('.download-btn');
    downloadLinks.forEach(link => link.addEventListener('click', handleDownloadClick));

    // 也攔截 auto-link 中殘留的 /download/ URL（兜底），避免跳轉到空白頁
    const autoLinks = container.querySelectorAll('a.auto-link');
    autoLinks.forEach(link => {
      if (link.href && link.href.includes('/download/')) {
        link.addEventListener('click', handleDownloadClick);
      }
    });

    const images = container.querySelectorAll('.generated-image');
    images.forEach(img => img.addEventListener('error', handleImageError));

    return () => {
      downloadLinks.forEach(link => link.removeEventListener('click', handleDownloadClick));
      autoLinks.forEach(link => {
        if (link.href && link.href.includes('/download/')) {
          link.removeEventListener('click', handleDownloadClick);
        }
      });
      images.forEach(img => img.removeEventListener('error', handleImageError));
    };
  }, [downloadHtml, imageHtml]);

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <div className="message-role">{role === 'user' ? 'You' : 'Assistant'}</div>
        <div className="message-text" ref={messageTextRef}>
          {/* 文字內容 - 可以隨 stream 更新 */}
          <div dangerouslySetInnerHTML={{ __html: textHtml }} />
          {/* Plotly 圖表 iframe 區域 — 獨立 memo 化元件，防止打字時閃爍 */}
          <ChartSection html={chartHtml} />
          {/* 下載檔案區域 */}
          {downloadHtml && (
            <div
              className="downloads-section"
              dangerouslySetInnerHTML={{ __html: downloadHtml }}
            />
          )}
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
});

function extractImagesFromContent(content) {
  if (!content) return { textHtml: '', imageHtml: '', chartHtml: '', downloadHtml: '' };

  let html = content;
  let imageHtml = '';
  let chartHtml = '';
  let downloadHtml = '';
  const foundImages = new Set();
  const foundCharts = new Set();
  const foundDownloads = new Set();

  // 先統一路徑分隔符號（Windows 反斜線轉正斜線）
  html = html.replace(/\\/g, '/');

  // Helper function to add image
  const addImage = (imgSrc, altText = 'Generated Image') => {
    // 統一規範化為 API_BASE/images/<filename>
    // 避免同一張圖片因路徑格式不同被重複渲染
    let normalizedSrc = imgSrc;
    // outputs/images/xxx.png → /agentapi/images/xxx.png
    if (normalizedSrc.startsWith('outputs/images/')) {
      normalizedSrc = `${IMAGES_BASE}/${normalizedSrc.replace('outputs/images/', '')}`;
    }
    // /images/xxx.png → /agentapi/images/xxx.png
    else if (normalizedSrc.startsWith('/images/')) {
      normalizedSrc = `${API_BASE}${normalizedSrc}`;
    }
    // http://localhost:XXXX/images/xxx.png → /agentapi/images/xxx.png
    else if (/^https?:\/\/localhost:\d+\/images\//.test(normalizedSrc)) {
      normalizedSrc = normalizedSrc.replace(/^https?:\/\/localhost:\d+/, API_BASE);
    }
    if (!foundImages.has(normalizedSrc)) {
      foundImages.add(normalizedSrc);
      imageHtml += `<div class="generated-image-container">
        <img src="${normalizedSrc}" alt="${altText}" class="generated-image" loading="lazy" />
        <a href="${normalizedSrc}" target="_blank" rel="noopener" class="image-link">🔗 View Full Size</a>
      </div>`;
    }
  };

  // Helper function to add Plotly chart iframe
  const addChart = (chartPath, title = 'Interactive Chart') => {
    // 確保使用 API_BASE 路徑
    let src = chartPath;
    if (src.startsWith('/charts/')) {
      src = `${API_BASE}${src}`;
    } else {
      // 統一成 API_BASE（防止其他 port 寫法）
      src = src.replace(/https?:\/\/localhost:\d+/, API_BASE);
    }
    if (!foundCharts.has(src)) {
      foundCharts.add(src);
      const safeTitle = title.replace(/"/g, '&quot;');
      chartHtml += `<div class="chart-container">
        <div class="chart-title">📊 ${safeTitle}</div>
        <iframe
          src="${src}"
          class="chart-iframe"
          frameborder="0"
          scrolling="no"
          title="${safeTitle}"
        ></iframe>
        <a href="${src}" target="_blank" rel="noopener" class="chart-link">🔗 獨立開啟圖表</a>
      </div>`;
    }
  };

  // Helper: add download button
  const addDownload = (url, filename) => {
    const downloadUrl = url.replace(/https?:\/\/localhost:\d+/, API_BASE);
    if (!foundDownloads.has(downloadUrl)) {
      foundDownloads.add(downloadUrl);
      const ext = filename.split('.').pop().toUpperCase();
      const iconMap = { PPTX:'📊', XLSX:'📗', CSV:'📄', PDF:'📕', DOCX:'📘', ZIP:'🗜️' };
      const icon = iconMap[ext] || '📎';
      downloadHtml += `<div class="download-container">
        <div class="download-info">
          <span class="download-icon">${icon}</span>
          <span class="download-filename">${filename}</span>
        </div>
        <a href="${downloadUrl}" download="${filename}" class="download-btn">
          ⬇ 下載檔案
        </a>
      </div>`;
    }
  };

  // --- 00. 偵測 DOWNLOAD: URL 格式（最優先）---
  // 格式: DOWNLOAD: /agentapi/download(s)/<filename> 或 DOWNLOAD: http://localhost:XXXX/download(s)/<filename>
  const downloadTagRegex = /DOWNLOAD:\s*((?:https?:\/\/localhost:\d+)?\/downloads?\/([\w\-_.%]+))/gi;
  html = html.replace(downloadTagRegex, (match, url, filename) => {
    addDownload(url, decodeURIComponent(filename));
    return '';
  });

  // 也偵測純 /download(s)/xxx 路徑（不帶 DOWNLOAD: 前綴），包含完整 URL 或相對路徑
  const downloadUrlRegex = /(?:https?:\/\/localhost:\d+)?\/downloads?\/([\w\-_.%]+)/gi;
  html = html.replace(downloadUrlRegex, (match, filename) => {
    addDownload(`${DOWNLOADS_BASE}/${filename}`, decodeURIComponent(filename));
    return '';
  });

  // --- 0. 先偵測圖表 URL，優先於一般 URL 處理 ---

  // 0a. Markdown 連結格式: [title](http://localhost:7777/charts/xxx.html)
  const chartMdLinkRegex = /\[([^\]]*)\]\(((?:https?:\/\/localhost:\d+)?\/charts\/[\w\-_.%]+\.html)\)/gi;
  html = html.replace(chartMdLinkRegex, (match, text, url) => {
    addChart(url, text || 'Interactive Chart');
    return '';
  });

  // 0b. 純 URL 格式（含或不含 host）: http://localhost:7777/charts/xxx.html 或 /charts/xxx.html
  const chartUrlRegex = /(?:https?:\/\/localhost:\d+)?(\/charts\/[\w\-_.%]+\.html)/gi;
  html = html.replace(chartUrlRegex, (match, path) => {
    const filename = path.split('/').pop().replace('.html', '');
    const title = filename.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    addChart(path, title);
    return '';
  });

  // 0c. 完整 localhost URL 圖片（含 Markdown ![]() 語法與純裸 URL）
  // 格式: http://localhost:XXXX/images/ComfyUI_XXXXX_.png
  // 這是 Team Leader 被指示輸出的標準格式，必須優先偵測
  const fullLocalhostImgMdRegex = /!?\[([^\]]*)\]\((https?:\/\/localhost:\d+\/images\/([\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)))\)/gi;
  html = html.replace(fullLocalhostImgMdRegex, (match, alt, fullUrl, filename) => {
    addImage(`${IMAGES_BASE}/${filename}`, alt || 'Generated Image');
    return '';
  });
  const fullLocalhostImgBareRegex = /(?<!["'(])(https?:\/\/localhost:\d+\/images\/([\w\-_.]+\.(?:png|jpg|jpeg|webp|gif)))(?!["')])/gi;
  html = html.replace(fullLocalhostImgBareRegex, (match, fullUrl, filename) => {
    addImage(`${IMAGES_BASE}/${filename}`);
    return '';
  });

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

  // 完整的 Markdown 轉換
  const textHtml = html
    // 程式碼區塊 (先處理，避免被其他規則影響)
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    // 行內程式碼
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 標題 (從 h4 到 h1，避免衝突)
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 水平線
    .replace(/^---$/gm, '<hr>')
    .replace(/^\*\*\*$/gm, '<hr>')
    // 粗體
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // 斜體
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // 無序列表項目 - 移除可能的前導數字（如 "- 23. 內容" → 只保留 "內容"）
    .replace(/^- (?:\d+[\.\)]\s*)?(.+)$/gm, '<li class="ul-item">$1</li>')
    // 有序列表項目（純數字開頭，非 bullet point）
    .replace(/^(\d+)[\.\)] (.+)$/gm, '<li class="ol-item" value="$1">$2</li>')
    // 一般 Markdown 連結（非圖片）
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
      // 如果是圖片連結，不處理（已經處理過）
      if (/\.(png|jpg|jpeg|webp|gif)$/i.test(url)) {
        return '';
      }
      return `<a href="${url}" target="_blank" rel="noopener" class="md-link">${text}</a>`;
    })
    // 自動偵測並連結純 URL (http/https)
    .replace(/(?<!["\'>])https?:\/\/[^\s<>\[\]"']+/g, (url) => {
      // 移除結尾的標點符號
      const cleanUrl = url.replace(/[.,;:!?)]+$/, '');
      const trailing = url.slice(cleanUrl.length);
      return `<a href="${cleanUrl}" target="_blank" rel="noopener" class="auto-link">${cleanUrl}</a>${trailing}`;
    })
    // 換行處理
    .replace(/\n/g, '<br>')
    // 將連續的列表項目包裝成列表
    .replace(/(<li class="ul-item">.*?<\/li>)(<br>)?(?=<li class="ul-item">|<br><li class="ul-item">)/g, '$1')
    .replace(/(<li class="ol-item">.*?<\/li>)(<br>)?(?=<li class="ol-item">|<br><li class="ol-item">)/g, '$1')
    // 清理列表之間的多餘 <br>
    .replace(/<\/li><br><li/g, '</li><li')
    // 清理多餘的空白行
    .replace(/(<br>){3,}/g, '<br><br>')
    // 清理標題後的 <br>
    .replace(/(<\/h[1-4]>)<br>/g, '$1')
    // 清理 <hr> 周圍的 <br>
    .replace(/<br><hr>/g, '<hr>')
    .replace(/<hr><br>/g, '<hr>');

  return { textHtml, imageHtml, chartHtml, downloadHtml };
}

export default Message;
