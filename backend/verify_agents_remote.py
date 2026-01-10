from agents_remote import creative_team
import asyncio

async def test_remote_team():
    print("🧪 Testing Creative Team with RemoteAgent...")
    
    # Test query that should trigger the Image Generator
    response = await creative_team.arun(
        "先網路蒐集Elon musk的人物特徵, 在畫一張他的自畫像",
        user_id="test-user-123",
    )
    
    print("\n✅ Team execution completed.")
    print(f"📝 Response content:\n{response.content}")

if __name__ == "__main__":
    asyncio.run(test_remote_team())
