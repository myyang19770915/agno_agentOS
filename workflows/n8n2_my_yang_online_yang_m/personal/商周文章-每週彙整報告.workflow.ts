import { workflow, node, links } from '@n8n-as-code/transformer';

// <workflow-map>
// Workflow : 商周文章 - 每週彙整報告
// Nodes   : 5  |  Connections: 4
//
// NODE INDEX
// ──────────────────────────────────────────────────────────────────
// Property name                    Node type (short)         Flags
// ScheduleTrigger                    scheduleTrigger
// GmailGetAll                        gmail                      [creds]
// CombineContent                     code
// OpenaiSummary                      openAi                     [creds]
// TelegramSend                       telegram                   [creds]
//
// ROUTING MAP
// ──────────────────────────────────────────────────────────────────
// ScheduleTrigger
//    → GmailGetAll
//      → CombineContent
//        → OpenaiSummary
//          → TelegramSend
// </workflow-map>

// =====================================================================
// METADATA DU WORKFLOW
// =====================================================================

@workflow({
    id: 'S0xZOx4Wnb7sB2ey',
    name: '商周文章 - 每週彙整報告',
    active: false,
    settings: {
        timezone: 'Asia/Taipei',
        executionOrder: 'v1',
        callerPolicy: 'workflowsFromSameOwner',
        availableInMCP: false,
    },
})
export class NodeWorkflow {
    // =====================================================================
    // CONFIGURATION DES NOEUDS
    // =====================================================================

    @node({
        id: '8a659dfb-2ceb-494a-87ba-87aee99670db',
        name: 'Schedule Trigger',
        type: 'n8n-nodes-base.scheduleTrigger',
        version: 1.3,
        position: [-800, 0],
    })
    ScheduleTrigger = {
        rule: {
            interval: [
                {
                    field: 'weeks',
                    weeksInterval: 1,
                    triggerAtDay: '1',
                    triggerAtHour: '8',
                    triggerAtMinute: 0,
                },
            ],
        },
    };

    @node({
        id: '36ea127d-6df8-4c67-9b94-65a362cd3733',
        name: 'Gmail Get All',
        type: 'n8n-nodes-base.gmail',
        version: 2.1,
        position: [-600, 0],
        credentials: { gmailOAuth2: { id: 'Leh7cdOXE6Fiumd6', name: 'Gmail account' } },
    })
    GmailGetAll = {
        resource: 'message',
        operation: 'getAll',
        returnAll: false,
        limit: 20,
        simple: true,
        filters: {
            q: 'subject:(商周 OR 商週) newer_than:7d',
        },
    };

    @node({
        id: 'ccd44d25-e1d3-496f-97a0-c0486664ea7c',
        name: 'Combine Content',
        type: 'n8n-nodes-base.code',
        version: 2,
        position: [-400, 0],
    })
    CombineContent = {
        mode: 'runOnceForAllItems',
        jsCode: `
const items = $input.all();

if (items.length === 0) {
  return [{ json: { combined: '本週無新商周文章。', count: 0 } }];
}

const articles = items.map((item, i) => {
  const subject = item.json.Subject || item.json.subject || '(無標題)';
  const snippet = item.json.snippet || item.json.Snippet || '';
  const from    = item.json.From    || item.json.from    || '';
  return \`【第 \${i + 1} 篇】\\n主旨：\${subject}\\n寄件人：\${from}\\n摘要：\${snippet}\`;
}).join('\\n\\n---\\n\\n');

return [{
  json: {
    combined: articles,
    count: items.length,
    week: new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })
  }
}];
`,
    };

    @node({
        id: 'df26ab52-d8e2-4140-b4a1-ef888ec6de2f',
        name: 'OpenAI Summary',
        type: 'n8n-nodes-base.openAi',
        version: 1.1,
        position: [-200, 0],
        credentials: { openAiApi: { id: 'wigRgsvNXuvrLgLL', name: 'OpenAi account' } },
    })
    OpenaiSummary = {
        resource: 'chat',
        chatModel: 'gpt-4o-mini',
        prompt: {
            messages: [
                {
                    role: 'system',
                    content: `你是一位資深商業分析師。請針對以下本週商周雜誌文章，輸出一份《每週商周精華報告》。

📋 報告格式：
1. 📌 本週重點主題（3-5 個 tag）
2. 📝 各篇重點摘要（每篇 2-3 句，保留關鍵數據或洞察）
3. 🔭 本週最值得關注的商業趨勢
4. 💡 行動建議（1-3 條，具體可執行）

⚠️ 規則：
- 僅用繁體中文
- 語氣精練、有洞察力
- 若本週無文章，直接回覆「本週無新商周文章」`,
                },
                {
                    role: 'user',
                    content: '={{ $json.combined }}',
                },
            ],
        },
        simplifyOutput: true,
        options: {},
    };

    @node({
        id: '6b8887e2-44dd-4c12-af23-eddf1c14f569',
        name: 'Telegram Send',
        type: 'n8n-nodes-base.telegram',
        version: 1.2,
        position: [0, 0],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    TelegramSend = {
        chatId: '7030555903',
        text: `=📰 *商周週報 {{ $('Combine Content').item.json.week }}*（共 {{ $('Combine Content').item.json.count }} 篇）

{{ $json.message.content }}`,
        additionalFields: {
            parse_mode: 'Markdown',
        },
    };

    // =====================================================================
    // ROUTAGE ET CONNEXIONS
    // =====================================================================

    @links()
    defineRouting() {
        this.ScheduleTrigger.out(0).to(this.GmailGetAll.in(0));
        this.GmailGetAll.out(0).to(this.CombineContent.in(0));
        this.CombineContent.out(0).to(this.OpenaiSummary.in(0));
        this.OpenaiSummary.out(0).to(this.TelegramSend.in(0));
    }
}
