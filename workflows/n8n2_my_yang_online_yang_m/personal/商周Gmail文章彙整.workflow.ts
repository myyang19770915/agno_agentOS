import { workflow, node, links } from '@n8n-as-code/transformer';

// <workflow-map>
// Workflow : 商周Gmail文章彙整1
// Nodes   : 6  |  Connections: 4
//
// NODE INDEX
// ──────────────────────────────────────────────────────────────────
// Property name                    Node type (short)         Flags
// GmailTrigger                       gmailTrigger               [creds]
// If_                                if                         
// OpenaiChatModel                    lmChatOpenAi               [creds]
// Gmail                              gmail                      [creds]
// Openai                             openAi                     [creds]
// Telegram                           telegram                   [creds]
//
// ROUTING MAP
// ──────────────────────────────────────────────────────────────────
// GmailTrigger
//    → If_
//      → Gmail
//        → Openai
//          → Telegram
// </workflow-map>

// =====================================================================
// METADATA DU WORKFLOW
// =====================================================================

@workflow({
    id: "YhIF91ngU1OOE6bj",
    name: "商周Gmail文章彙整1",
    active: true,
    settings: { executionOrder: "v1", binaryMode: "separate", availableInMCP: false, timeSavedMode: "fixed", timezone: "Asia/Taipei", callerPolicy: "workflowsFromSameOwner" }
})
export class Gmail1Workflow {

    // =====================================================================
// CONFIGURATION DES NOEUDS
// =====================================================================

    @node({
        id: "72b0d053-e822-49fc-b93c-21ec1e9242b2",
        name: "Gmail Trigger",
        type: "n8n-nodes-base.gmailTrigger",
        version: 1.2,
        position: [-448, 112],
        credentials: {gmailOAuth2:{id:"Leh7cdOXE6Fiumd6",name:"Gmail account"}}
    })
    GmailTrigger = {
        pollTimes: {
            item: [
                {
                    mode: "everyMinute"
                }
            ]
        },
        filters: {}
    };

    @node({
        id: "04f0eec6-f7d9-41e6-a21c-8146c22f45e2",
        name: "If",
        type: "n8n-nodes-base.if",
        version: 2.2,
        position: [-224, 112]
    })
    If_ = {
        conditions: {
            options: {
                caseSensitive: true,
                leftValue: "",
                typeValidation: "strict",
                version: 2
            },
            conditions: [
                {
                    id: "d3b024d5-6d2b-44e3-93ef-46aab972d607",
                    leftValue: "={{ $json.Subject }}",
                    rightValue: "=商周",
                    operator: {
                        type: "string",
                        operation: "contains"
                    }
                },
                {
                    id: "8314e3e4-de41-476c-a035-24f2880f653f",
                    leftValue: "={{ $json.Subject }}",
                    rightValue: "商週",
                    operator: {
                        type: "string",
                        operation: "contains"
                    }
                }
            ],
            combinator: "or"
        },
        options: {}
    };

    @node({
        id: "6ada019f-2be5-4b95-be3d-dae2c74fd0f2",
        name: "OpenAI Chat Model",
        type: "@n8n/n8n-nodes-langchain.lmChatOpenAi",
        version: 1,
        position: [208, 272],
        credentials: {openAiApi:{id:"9aDqN2jUUtVMmHT6",name:"OpenAi account 2"}}
    })
    OpenaiChatModel = {
        options: {}
    };

    @node({
        id: "37385871-b3ef-4921-a7c5-097b40aabc56",
        webhookId: "ed281c34-8838-4d6f-90bd-5fb5159aca47",
        name: "Gmail",
        type: "n8n-nodes-base.gmail",
        version: 2.1,
        position: [0, 0],
        credentials: {gmailOAuth2:{id:"Leh7cdOXE6Fiumd6",name:"Gmail account"}}
    })
    Gmail = {
        operation: "get",
        messageId: "={{ $json.id }}",
        simple: false,
        options: {
            dataPropertyAttachmentsPrefixName: "attachment_"
        }
    };

    @node({
        id: "3713450f-fff8-4031-8c42-af0b99257efb",
        name: "OpenAI",
        type: "@n8n/n8n-nodes-langchain.openAi",
        version: 1.7,
        position: [224, 0],
        credentials: {openAiApi:{id:"wigRgsvNXuvrLgLL",name:"OpenAi account"}}
    })
    Openai = {
        modelId: {
            __rl: true,
            value: "gpt-5-mini",
            mode: "list",
            cachedResultName: "GPT-5-MINI"
        },
        messages: {
            values: [
                {
                    content: "={{ $json.text }}"
                },
                {
                    content: `=請依照內容的段落與章節, 分別彙整出以下內容
其中每一段落或章節需要包含的有: 
 -作者
 -關鍵字
 -彙整摘要
 -具體的方法與建議`,
                    role: "system"
                }
            ]
        },
        options: {}
    };

    @node({
        id: "4298e867-dd02-4e86-b7a1-5f7bf3ec4712",
        webhookId: "8196d7fd-9992-4b91-8372-057854f0cd74",
        name: "Telegram",
        type: "n8n-nodes-base.telegram",
        version: 1.2,
        position: [592, 0],
        credentials: {telegramApi:{id:"A9eSh4fHLRD97r9j",name:"Telegram account"}}
    })
    Telegram = {
        chatId: "7030555903",
        text: "={{ $json.message.content }}",
        additionalFields: {}
    };


    // =====================================================================
// ROUTAGE ET CONNEXIONS
// =====================================================================

    @links()
    defineRouting() {
        this.GmailTrigger.out(0).to(this.If_.in(0));
        this.If_.out(0).to(this.Gmail.in(0));
        this.Gmail.out(0).to(this.Openai.in(0));
        this.Openai.out(0).to(this.Telegram.in(0));
    }
}