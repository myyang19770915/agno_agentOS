import { workflow, node, links } from '@n8n-as-code/transformer';

// <workflow-map>
// Workflow : Telegram AI Bot
// Nodes   : 23  |  Connections: 11
//
// NODE INDEX
// ──────────────────────────────────────────────────────────────────
// Property name                    Node type (short)         Flags
// CheckChatId                        if
// Wait3Seconds                       wait
// SendUnauthorizedInfoTelegram       telegram                   [creds]
// SendResponseTelegram               telegram                   [creds]
// CheckIfStart                       if
// NoOperation                        noOp
// StickyNote5                        stickyNote
// TelegramTrigger                    telegramTrigger            [creds]
// StickyNote6                        stickyNote
// StickyNote7                        stickyNote
// StickyNote8                        stickyNote
// SendTypingActionTelegram1          telegram                   [creds]
// StickyNote9                        stickyNote
// StickyNote11                       stickyNote
// SendTypingActionTelegram2          telegram                   [creds]
// StickyNote                         stickyNote
// OpenaiChatModel                    lmChatOpenAi               [creds] [ai_languageModel]
// WindowBufferMemory                 memoryBufferWindow         [ai_memory]
// Calculator                         toolCalculator             [ai_tool]
// HttpRequest                        httpRequest
// SendResponseTelegram1              telegram                   [creds]
// Wait                               wait
// AiAgent                            agent                      [AI]
//
// ROUTING MAP
// ──────────────────────────────────────────────────────────────────
// TelegramTrigger
//    → CheckIfStart
//      → NoOperation
//     .out(1) → CheckChatId
//        → SendTypingActionTelegram1
//          → AiAgent
//            → SendResponseTelegram
//       .out(1) → SendTypingActionTelegram2
//          → Wait3Seconds
//            → SendUnauthorizedInfoTelegram
// HttpRequest
//    → Wait
//      → SendResponseTelegram1
//
// AI CONNECTIONS
// AiAgent.uses({ ai_languageModel: OpenaiChatModel, ai_memory: WindowBufferMemory, ai_tool: [Calculator] })
// </workflow-map>

// =====================================================================
// METADATA DU WORKFLOW
// =====================================================================

@workflow({
    id: 'sCCitZgNNuEmyM7Z',
    name: 'Telegram AI Bot',
    active: true,
    tags: ['Chatbot', 'telegram'],
    settings: { executionOrder: 'v1', binaryMode: 'separate', availableInMCP: false },
})
export class TelegramAiBotWorkflow {
    // =====================================================================
    // CONFIGURATION DES NOEUDS
    // =====================================================================

    @node({
        id: '805f8d17-d3b9-44cb-a2f0-f2353d2ff76f',
        name: 'Check chat ID',
        type: 'n8n-nodes-base.if',
        version: 1,
        position: [880, 880],
    })
    CheckChatId = {
        conditions: {
            number: [
                {
                    value1: '={{ $json.message.chat.id }}',
                    operation: 'equal',
                    value2: 7030555903,
                },
            ],
        },
    };

    @node({
        id: '905cd085-cfed-4ff7-9daa-992c80b33157',
        webhookId: '5927178d-1fed-4ee6-bcad-c83fec83c92a',
        name: 'Wait 3 seconds',
        type: 'n8n-nodes-base.wait',
        version: 1,
        position: [1360, 1040],
    })
    Wait3Seconds = {
        amount: 3,
        unit: 'seconds',
    };

    @node({
        id: '08b65628-e9f8-4964-a0e8-8c3d5c4ea9e2',
        webhookId: '645035d8-2cc6-4aff-9623-e58dba4d6d2c',
        name: 'Send unauthorized info [TELEGRAM]',
        type: 'n8n-nodes-base.telegram',
        version: 1,
        position: [1552, 1040],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    SendUnauthorizedInfoTelegram = {
        chatId: "={{ $node['Telegram trigger'].json.message.chat.id }}",
        text: "I'm not authorized to speak with you. ",
        additionalFields: {},
    };

    @node({
        id: '1ecf5047-ff21-4fdb-94c4-47ad8057ccc2',
        webhookId: 'ccafb379-20d5-427f-9212-38cd2cf6f48f',
        name: 'Send response [TELEGRAM]',
        type: 'n8n-nodes-base.telegram',
        version: 1,
        position: [1968, 704],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    SendResponseTelegram = {
        chatId: "={{ $node['Check chat ID'].json.message.chat.id }}",
        text: '={{ $json.output }}',
        additionalFields: {},
    };

    @node({
        id: '1055f04f-824c-4594-86c7-3f7fcfbf2fc3',
        name: 'Check if start',
        type: 'n8n-nodes-base.if',
        version: 1,
        position: [656, 704],
    })
    CheckIfStart = {
        conditions: {
            string: [
                {
                    value1: '={{ $json.message.text }}',
                    value2: '/start',
                },
            ],
        },
    };

    @node({
        id: 'a0735b3a-5e22-4fd7-b5c8-ca217dc6ee71',
        name: 'No operation',
        type: 'n8n-nodes-base.noOp',
        version: 1,
        position: [880, 480],
    })
    NoOperation = {};

    @node({
        id: 'a5bf73a0-2784-498d-bea8-b2b403324e72',
        name: 'Sticky Note5',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [416, 256],
    })
    StickyNote5 = {
        content: `## ⚠️ Note

1. Complete video guide for this workflow is available [on my YouTube](https://www.youtube.com/watch?v=Gc2lW5BiGDQ). 
2. Remember to add your credentials and configure nodes (covered in the video guide).
3. If you like this workflow, please subscribe to [my YouTube channel](https://www.youtube.com/@workfloows) and/or [my newsletter](https://workfloows.com/).

**Thank you for your support!**`,
        height: 258.9141682442004,
        width: 382.8182353336517,
    };

    @node({
        id: 'f457ec23-bf1a-4a65-b35e-733d4b7f82be',
        webhookId: '64456f84-9a61-4ccc-a28c-3aca7a498103',
        name: 'Telegram trigger',
        type: 'n8n-nodes-base.telegramTrigger',
        version: 1,
        position: [448, 704],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    TelegramTrigger = {
        updates: ['message'],
        additionalFields: {},
    };

    @node({
        id: '21add0f1-8332-4fa5-af38-d7511165cb52',
        name: 'Sticky Note6',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [416, 544],
    })
    StickyNote6 = {
        content: `## Trigger
Remember to add credentials of your Telegram bot.`,
        height: 339.51767272727324,
        width: 182.4715262478496,
    };

    @node({
        id: 'b66e7420-d2fa-4996-b03b-ae3cb9c54aaa',
        name: 'Sticky Note7',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [608, 544],
    })
    StickyNote7 = {
        content: `## Ignore start
This node will ignore initial \`\`\`/start\`\`\` message that is sent by first conversation with bot.`,
        height: 339.51767272727324,
        width: 182.4715262478496,
    };

    @node({
        id: 'ed629f3e-9b25-4c4f-bc5d-656d83043995',
        name: 'Sticky Note8',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [832, 688],
    })
    StickyNote8 = {
        content: `## Authorize
Change default value \`\`\`0\`\`\` to your 10-digit chat ID to authorize conversation and disable other people to talk to your bot.`,
        height: 367.74256847311284,
        width: 182.4715262478496,
    };

    @node({
        id: '6285eea7-9783-4ab1-a3ae-dd0c3dfe2a0a',
        webhookId: '55ce5602-8541-44e2-bf3d-a3613df95276',
        name: 'Send typing action [TELEGRAM] [1]',
        type: 'n8n-nodes-base.telegram',
        version: 1,
        position: [1152, 688],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    SendTypingActionTelegram1 = {
        operation: 'sendChatAction',
        chatId: '={{ $json.message.chat.id }}',
    };

    @node({
        id: '5745a0c2-3c00-42e9-b26b-1785caff0e8e',
        name: 'Sticky Note9',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [1088, 896],
    })
    StickyNote9 = {
        content: `## Send "unauthorized" message
When unknown user (chat ID) wants to come into interaction with bot, workflow will send "typing" action, wait 3 seconds and respond: *"I'm not authorized to speak with you"*.`,
        height: 339.42690909090965,
        width: 643.3545239632286,
    };

    @node({
        id: '9d02bc59-f6d7-4b08-adea-b9711d3f4127',
        name: 'Sticky Note11',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [1120, 544],
    })
    StickyNote11 = {
        content: `## Generate response
This sequence sends "typing action", gets answer from GPT and returns message to authorized user. Feel free to play with prompt, configuration etc.`,
        height: 339.42690909090965,
        width: 1155.3587425463136,
        color: 6,
    };

    @node({
        id: '815ec3c1-568a-4065-aa0c-41fc6df9458d',
        webhookId: 'fc917f4d-f56a-41ff-8378-f95431f7e0d4',
        name: 'Send typing action [TELEGRAM] [2]',
        type: 'n8n-nodes-base.telegram',
        version: 1,
        position: [1152, 1040],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    SendTypingActionTelegram2 = {
        operation: 'sendChatAction',
        chatId: '={{ $json.message.chat.id }}',
    };

    @node({
        id: '4846b052-65a2-4752-aa4e-7c37f5ef5e8e',
        name: 'Sticky Note',
        type: 'n8n-nodes-base.stickyNote',
        version: 1,
        position: [48, 256],
    })
    StickyNote = {
        content: `## 🦜🔗 Add LangChain 

**This is just a basic workflow.** If you want to make your bot more powerful, consider installing [FlowiseAI](https://flowiseai.com/) (LangChain UI) on your server and connecting your bot via simple cURL (HTTP Request node). I cover example [in my YouTube video](https://www.youtube.com/watch?v=Gc2lW5BiGDQ).

Installation guides and other data about FlowiseAI can be found [here](https://github.com/FlowiseAI/Flowise).`,
        height: 258.16986559669937,
        width: 345.7880926620822,
    };

    @node({
        id: 'd1e45e17-e00f-47a0-8fe6-8a1d2dcecce9',
        name: 'OpenAI Chat Model',
        type: '@n8n/n8n-nodes-langchain.lmChatOpenAi',
        version: 1,
        position: [1312, 784],
        credentials: { openAiApi: { id: 'wigRgsvNXuvrLgLL', name: 'OpenAi account' } },
    })
    OpenaiChatModel = {
        options: {},
    };

    @node({
        id: 'ccca774c-9129-49fd-b1ae-13c9997f909c',
        name: 'Window Buffer Memory',
        type: '@n8n/n8n-nodes-langchain.memoryBufferWindow',
        version: 1.2,
        position: [1424, 784],
    })
    WindowBufferMemory = {
        sessionIdType: 'customKey',
        sessionKey: "={{ $('Check chat ID').item.json.message.chat.id }}",
        contextWindowLength: 10,
    };

    @node({
        id: 'cd169e41-bddd-488c-95f7-d382e5353e1f',
        name: 'Calculator',
        type: '@n8n/n8n-nodes-langchain.toolCalculator',
        version: 1,
        position: [1648, 784],
    })
    Calculator = {};

    @node({
        id: 'd2c9af2b-5a55-4c17-8c9c-10f60c0e001d',
        name: 'HTTP Request',
        type: 'n8n-nodes-base.httpRequest',
        version: 4.2,
        position: [1440, 384],
    })
    HttpRequest = {
        method: 'POST',
        url: 'http://localhost:3000/api/v1/prediction/b2aa437b-2149-49fe-a9e9-5258853715b5',
        sendBody: true,
        bodyParameters: {
            parameters: [
                {
                    name: 'question',
                    value: '{{ $node["Telegram trigger"].json["message"]["text"] }}',
                },
            ],
        },
        options: {
            response: {
                response: {
                    responseFormat: 'text',
                },
            },
        },
    };

    @node({
        id: 'a6abfd14-9cd7-4367-9dec-587a0d7a18db',
        webhookId: '707a7f67-ceb2-475a-9cf0-3667d54c5f95',
        name: 'Send response [TELEGRAM]1',
        type: 'n8n-nodes-base.telegram',
        version: 1,
        position: [1936, 384],
        credentials: { telegramApi: { id: 'A9eSh4fHLRD97r9j', name: 'Telegram account' } },
    })
    SendResponseTelegram1 = {
        chatId: "={{ $node['Check chat ID'].json.message.chat.id }}",
        text: '={{ $json.data }}',
        additionalFields: {},
    };

    @node({
        id: 'ed44b065-cf75-4af3-a4e1-5c4b5b761d01',
        webhookId: '1c9aca12-3c73-4ecd-9fde-553ee84945d7',
        name: 'Wait',
        type: 'n8n-nodes-base.wait',
        version: 1.1,
        position: [1648, 384],
    })
    Wait = {};

    @node({
        id: 'dd27ec26-6810-4858-afcb-fedb1956effd',
        name: 'AI Agent',
        type: '@n8n/n8n-nodes-langchain.agent',
        version: 1.6,
        position: [1392, 640],
    })
    AiAgent = {
        promptType: 'define',
        text: '={{ $node["Telegram trigger"].json["message"]["text"] }}',
        options: {
            systemMessage: `You are a helpful assistant, 
如果確實不知道答案，請回答不知道，不要捏造
以繁體中文回答`,
        },
    };

    // =====================================================================
    // ROUTAGE ET CONNEXIONS
    // =====================================================================

    @links()
    defineRouting() {
        this.CheckChatId.out(0).to(this.SendTypingActionTelegram1.in(0));
        this.CheckChatId.out(1).to(this.SendTypingActionTelegram2.in(0));
        this.Wait3Seconds.out(0).to(this.SendUnauthorizedInfoTelegram.in(0));
        this.CheckIfStart.out(0).to(this.NoOperation.in(0));
        this.CheckIfStart.out(1).to(this.CheckChatId.in(0));
        this.TelegramTrigger.out(0).to(this.CheckIfStart.in(0));
        this.SendTypingActionTelegram1.out(0).to(this.AiAgent.in(0));
        this.SendTypingActionTelegram2.out(0).to(this.Wait3Seconds.in(0));
        this.HttpRequest.out(0).to(this.Wait.in(0));
        this.Wait.out(0).to(this.SendResponseTelegram1.in(0));
        this.AiAgent.out(0).to(this.SendResponseTelegram.in(0));

        this.AiAgent.uses({
            ai_languageModel: this.OpenaiChatModel.output,
            ai_memory: this.WindowBufferMemory.output,
            ai_tool: [this.Calculator.output],
        });
    }
}
