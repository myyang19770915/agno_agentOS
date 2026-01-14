from agents_remote import creative_team
import asyncio

async def test_remote_team():
    print("🧪 Testing Creative Team with RemoteAgent...")
    print("=" * 60)
    
    # Test query that should trigger the Image Generator
    response = await creative_team.arun(
        "先網路蒐集國父孫中山的人物特徵, 在畫一張他的自畫像",
        user_id="test-user-123",
        stream_intermediate_steps=True,  # 開啟中間步驟輸出
        debug_mode=True,  # 開啟 debug 模式
    )
    
    print("\n" + "=" * 60)
    print("✅ Team execution completed.")
    print("=" * 60)
    
    # Debug: 印出 response 的所有屬性
    print("\n🔍 DEBUG - Response attributes:")
    for attr in dir(response):
        if not attr.startswith('_'):
            try:
                value = getattr(response, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except Exception as e:
                print(f"  {attr}: <Error: {e}>")
    
    print(f"\n📝 Response content:\n{response.content}")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_remote_team())
