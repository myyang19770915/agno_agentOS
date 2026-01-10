import asyncio
from agno.agent import RemoteAgent

async def main():
    # 連接到運行在 port 9999 的 Image Agent
    # 方法一, 直接透過agentos 協議連接
    agent_via_agentos = RemoteAgent(
        base_url="http://localhost:9999",
        agent_id="image-generator",
        protocol="agentos",  # 預設值
    )
    print("\n1️⃣ 通過 AgentOS 協議訪問:")
    response1 = await agent_via_agentos.arun(
        "一個3D皮卡斯風格的日本女學生",
        session_id="session-123",
        user_id="user-123",
    )
    print(f"Response: {response1.content}")

    # ============================================================================
    # 方式 2: 使用 A2A 協議（跨框架標準）
    # ============================================================================
    # A2A protocol endpoint path: /a2a/agents/{agent_id}
    agent_via_a2a = RemoteAgent(
        base_url="http://localhost:9999/a2a/agents/image-generator",
        agent_id="image-generator",
        protocol="a2a",
        a2a_protocol="rest",
    )
    
    print("\n2️⃣ 通過 A2A 協議訪問:")
    print("🎨 Sending request to Image Agent...")
    prompt = "一個3D皮卡斯風格的中國女學生"
    
    response2 = await agent_via_a2a.arun(
        prompt,
        session_id="session-456",  # 映射到 context_id
        user_id="user-456",
    )
    print(f"Response: {response2.content}")
    
    # 呼叫遠端 Agent
    # try:
    #     response = await agent_via_a2a.arun(prompt)
        
    #     print("\n✅ Response received:")
    #     if hasattr(response, 'content'):
    #         print(response.content)
    #     else:
    #         print(response)
            
    # except Exception as e:
    #     print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
