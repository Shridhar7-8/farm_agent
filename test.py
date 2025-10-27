"""
Debug test for deployed agent with detailed event logging
"""
import asyncio
import vertexai
from vertexai import agent_engines
import json

async def debug_test():
    vertexai.init(project="digitalhuman-445007", location="us-east4")
    
    print("🔗 Connecting to deployed agent...")
    remote_app = agent_engines.get("projects/396992623272/locations/us-east4/reasoningEngines/4796790999986733056")
    print("✅ Connected!")
    
    print("\n📝 Creating session...")
    session = await remote_app.async_create_session(user_id="debug_test")
    session_id = session.id if hasattr(session, 'id') else session.get('id', str(session))
    print(f"✅ Session: {session_id}")
    
    query = "What are the soil requirements for rice cultivation?"
    print(f"\n❓ Query: {query}")
    print("⏳ Waiting for response...")
    print("\n📊 Event Stream (detailed):")
    print("="*70)
    
    events = []
    event_count = 0
    
    try:
        async for event in remote_app.async_stream_query(
            user_id="debug_test",
            session_id=session_id,
            message=query
        ):
            event_count += 1
            events.append(event)
            
            print(f"\n🔔 Event #{event_count}:")
            print(f"Type: {type(event)}")
            
            # Try to extract content in different ways
            if isinstance(event, dict):
                print(f"Dict keys: {event.keys()}")
                
                if 'content' in event:
                    print(f"Content: {event['content']}")
                
                if 'error' in event:
                    print(f"❌ Error in event: {event['error']}")
                    
                if 'parts' in event:
                    print(f"Parts: {event['parts']}")
                    
                # Print full event for debugging
                try:
                    print(f"Full event: {json.dumps(event, indent=2, default=str)[:500]}")
                except:
                    print(f"Full event: {str(event)[:500]}")
            else:
                # For non-dict events
                print(f"Event attributes: {dir(event)}")
                if hasattr(event, 'content'):
                    print(f"Content: {event.content}")
                if hasattr(event, 'error'):
                    print(f"❌ Error: {event.error}")
                if hasattr(event, 'data'):
                    print(f"Data: {event.data}")
            
            print("-"*70)
    
    except Exception as e:
        print(f"\n❌ Exception during streaming: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n📊 Total events received: {event_count}")
    
    if event_count == 0:
        print("\n❌ PROBLEM: No events received at all")
        print("\n🔍 Possible issues:")
        print("1. Agent might be encountering an internal error")
        print("2. RAG permissions might still be propagating (wait 2-5 minutes)")
        print("3. Agent configuration might have issues")
        print("\n💡 Check agent logs:")
        print(f"https://console.cloud.google.com/logs/query?project=digitalhuman-445007")
        return False
    
    # Try to find final response
    final_responses = []
    for event in events:
        try:
            if isinstance(event, dict):
                if event.get("content", {}).get("parts"):
                    text = event["content"]["parts"][0].get("text")
                    if text and not event["content"]["parts"][0].get("function_call"):
                        final_responses.append(text)
        except:
            pass
    
    if final_responses:
        print("\n✅ Found response(s):")
        print("="*70)
        for i, resp in enumerate(final_responses, 1):
            print(f"\nResponse {i}:")
            print(resp)
            print("-"*70)
        
        # Check if RAG is working
        combined_response = " ".join(final_responses)
        if "error" in combined_response.lower() or "cannot access" in combined_response.lower():
            print("\n❌ RAG ERROR: Cannot access knowledge base")
            return False
        else:
            print("\n✅ SUCCESS! RAG appears to be working!")
            return True
    else:
        print("\n⚠️ Events received but no text response found")
        print("Check the event details above for more information")
        return False

if __name__ == "__main__":
    print("🔍 Debug Test for Deployed Farm Agent")
    print("="*70)
    try:
        result = asyncio.run(debug_test())
        
        if not result:
            print("\n" + "="*70)
            print("🔧 TROUBLESHOOTING STEPS:")
            print("="*70)
            print("\n1. Check Agent Logs:")
            print("   https://console.cloud.google.com/logs/query?project=digitalhuman-445007")
            print("   Filter by: 'reasoningEngines'")
            print("\n2. Verify RAG Permissions (wait 2-5 minutes after granting):")
            print("   The permissions need time to propagate")
            print("\n3. Check if agent is running:")
            print("   https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=digitalhuman-445007")
            print("\n4. Try granting additional permission:")
            print("   gcloud projects add-iam-policy-binding digitalhuman-445007 \\")
            print("     --member='serviceAccount:service-396992623272@gcp-sa-vertex-rag.iam.gserviceaccount.com' \\")
            print("     --role='roles/aiplatform.user'")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()