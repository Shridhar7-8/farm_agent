"""
Deployment script for Farm Management Agent to Vertex AI Agent Engine

This script handles the deployment of the farm management agent to Agent Engine
with proper configuration and error handling, including RAG corpus access.
"""

import asyncio
import os
import vertexai
from vertexai import agent_engines
from agent_engine_app import app, farm_management_agent
from src.config.config import config
from src.tools.utils import logger
import logging

# Set up deployment logging
logging.basicConfig(level=logging.INFO)
deployment_logger = logging.getLogger("deployment")

class AgentEngineDeployer:
    def __init__(self):
        self.project_id = config.vertexai.project_id
        self.location = config.vertexai.location
        self.staging_bucket = os.getenv("STAGING_BUCKET", "gs://digitalhuman-445007-agent-staging")
        self.display_name = os.getenv("AGENT_DISPLAY_NAME", "Farm Management Agent")
        self.service_account = "rag-service-account@digitalhuman-445007.iam.gserviceaccount.com"  # Newly added service account
        
        deployment_logger.info(f"Initializing deployment for project: {self.project_id}")
        deployment_logger.info(f"Location: {self.location}")
        deployment_logger.info(f"Staging bucket: {self.staging_bucket}")
        deployment_logger.info(f"RAG Corpus: {config.vertexai.rag_corpus_name}")
        deployment_logger.info(f"Service Account: {self.service_account}")  # Log the service account

    async def test_local_agent(self):
        """Test the agent locally before deployment"""
        deployment_logger.info("🧪 Testing agent locally before deployment...")
        
        try:
            # Create a local session
            session = await app.async_create_session(user_id="test_user_123")
            session_id = session.id if hasattr(session, 'id') else session.get('id', str(session))
            deployment_logger.info(f"✅ Local session created: {session_id}")
            
            # Test a simple query
            test_query = "What are the soil requirements for growing rice?"
            deployment_logger.info(f"🔍 Testing query: {test_query}")
            
            events = []
            async for event in app.async_stream_query(
                user_id="test_user_123",
                session_id=session_id,
                message=test_query,
            ):
                events.append(event)
                
            if events:
                deployment_logger.info(f"✅ Local test successful - received {len(events)} events")
                return True
            else:
                deployment_logger.error("❌ Local test failed - no events received")
                return False
                
        except Exception as e:
            deployment_logger.error(f"❌ Local test failed: {e}")
            return False
    
    async def deploy_to_agent_engine(self):
        """Deploy the agent to Agent Engine using correct SDK method"""
        deployment_logger.info("🚀 Starting deployment to Agent Engine...")
        
        try:
            # Deploy the agent using the correct Agent Engine method
            deployment_logger.info("📦 Packaging and deploying agent...")
            
            # CRITICAL: Set environment variables for RAG access in deployed environment
            deployment_logger.info(f"🔧 Configuring RAG corpus access: {config.vertexai.rag_corpus_name}")
            
           
            remote_app = agent_engines.create(
                app,
                display_name=self.display_name,
                description="AI-powered farm management assistant with memory, planning, and multi-agent capabilities",
                requirements=[
                    "vertexai>=1.0.0",
                    "google-cloud-aiplatform[adk,agent_engines]>=1.111.0",
                    "google-adk>=1.0.0", 
                    "pydantic>=2.0.0",
                    "aiohttp>=3.13.0",
                    "python-dotenv>=1.1.1",
                    "loguru>=0.7.3"
                ],
                extra_packages=["src/"],  # Include the entire src directory
                env_vars={
                    # Pass environment variables to deployed agent
                    "PROJECT_ID": self.project_id,
                    "LOCATION": self.location,
                    "MODEL": config.vertexai.model_name,
                    "RAG_CORPUS_NAME": config.vertexai.rag_corpus_name,
                    "SHEETS_BASE_URL": config.base_url_sheets
                },
                service_account=self.service_account  # Use the new service account
            )
            
            deployment_logger.info("✅ Deployment successful!")
            deployment_logger.info(f"🎯 Agent resource name: {remote_app.resource_name}")
            deployment_logger.info(f"📚 RAG Corpus configured: {config.vertexai.rag_corpus_name}")
            
            # Grant RAG corpus permissions to the deployed agent's service account
            await self._grant_rag_permissions(remote_app.resource_name)
            
            return remote_app
            
        except Exception as e:
            deployment_logger.error(f"❌ Deployment failed: {e}")
            raise
    
    async def _grant_rag_permissions(self, agent_resource_name: str):
        """Grant RAG corpus access permissions to the deployed agent."""
        try:
            deployment_logger.info("🔐 Configuring RAG corpus permissions...")
            
            # Extract service account from agent resource name
            # Format: projects/{project}/locations/{location}/agents/{agent_id}
            
            deployment_logger.info(f"""
📋 MANUAL PERMISSION SETUP REQUIRED:

To enable RAG access for your deployed agent, run this command:

gcloud projects add-iam-policy-binding {self.project_id} \\
  --member="serviceAccount:service-{self.project_id}@gcp-sa-aiplatform.iam.gserviceaccount.com" \\
  --role="roles/aiplatform.ragUser"

OR grant permissions in the console:
1. Go to: https://console.cloud.google.com/iam-admin/iam?project={self.project_id}
2. Find: service-{self.project_id}@gcp-sa-aiplatform.iam.gserviceaccount.com
3. Add role: "Vertex AI RAG Data Service Agent" or "roles/aiplatform.ragUser"

RAG Corpus: {config.vertexai.rag_corpus_name}
""")
            
            deployment_logger.info("✅ Permission instructions provided")
            
        except Exception as e:
            deployment_logger.warning(f"⚠️ Could not automatically configure RAG permissions: {e}")
            deployment_logger.warning("You may need to manually grant RAG access permissions")
    
    async def test_deployed_agent(self, remote_app):
        """Test the deployed agent"""
        deployment_logger.info("🔍 Testing deployed agent...")
        
        try:
            # Create a remote session
            remote_session = await remote_app.async_create_session(user_id="test_user_deployment")
            remote_session_id = remote_session.id if hasattr(remote_session, 'id') else remote_session.get('id', str(remote_session))
            deployment_logger.info(f"✅ Remote session created: {remote_session_id}")
            
            # Test query on deployed agent - SPECIFICALLY TEST RAG
            test_query = "What are the climatic and soil requirements to grow rice?"
            deployment_logger.info(f"🌾 Testing deployed agent with RAG query: {test_query}")
            deployment_logger.info("📚 This query should trigger the RAG agent to access agricultural knowledge base")
            
            events = []
            async for event in remote_app.async_stream_query(
                user_id="test_user_deployment",
                session_id=remote_session_id,
                message=test_query,
            ):
                events.append(event)
                
            if events:
                deployment_logger.info(f"✅ Deployed agent test successful - received {len(events)} events")
                
                # Extract final response for display
                final_responses = [
                    e for e in events
                    if e.get("content", {}).get("parts", [{}])[0].get("text")
                    and not e.get("content", {}).get("parts", [{}])[0].get("function_call")
                ]
                
                if final_responses:
                    response_text = final_responses[0]["content"]["parts"][0]["text"]
                    deployment_logger.info(f"📋 Sample response: {response_text[:200]}...")
                    
                    # Check if RAG was actually used
                    if "RAG" in response_text or "knowledge base" in response_text.lower() or len(response_text) > 300:
                        deployment_logger.info("✅ RAG appears to be working - detailed agricultural response received")
                    else:
                        deployment_logger.warning("⚠️ RAG might not be working - response seems generic")
                        deployment_logger.warning("Check if RAG corpus permissions are properly configured")
                
                return True
            else:
                deployment_logger.error("❌ Deployed agent test failed - no events received")
                return False
                
        except Exception as e:
            deployment_logger.error(f"❌ Deployed agent test failed: {e}")
            return False

async def main():
    """Main deployment function"""
    deployment_logger.info("🌾 Farm Management Agent - Agent Engine Deployment")
    deployment_logger.info("=" * 70)
    
    deployer = AgentEngineDeployer()
    
    try:
        # Step 1: Test locally
        deployment_logger.info("📋 Step 1: Local Testing")
        if not await deployer.test_local_agent():
            deployment_logger.error("❌ Local testing failed. Aborting deployment.")
            return
        
        # Step 2: Deploy to Agent Engine
        deployment_logger.info("\n📋 Step 2: Agent Engine Deployment")
        remote_app = await deployer.deploy_to_agent_engine()
        
        # Step 3: Test deployed agent
        deployment_logger.info("\n📋 Step 3: Deployment Verification")
        if await deployer.test_deployed_agent(remote_app):
            deployment_logger.info("\n🎉 SUCCESS: Farm Management Agent deployed successfully!")
            deployment_logger.info(f"🔗 Resource Name: {remote_app.resource_name}")
            deployment_logger.info(f"🌐 Access via: https://console.cloud.google.com/vertex-ai/agents/agent-engines")
        else:
            deployment_logger.warning("\n⚠️ Deployment completed but verification test failed")
            deployment_logger.info(f"🔗 Resource Name: {remote_app.resource_name}")
            deployment_logger.info(f"🌐 Access via: https://console.cloud.google.com/vertex-ai/agents/agent-engines")
            
    except Exception as e:
        deployment_logger.error(f"\n💥 DEPLOYMENT FAILED: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        deployment_logger.info("\n🛑 Deployment interrupted by user")
    except Exception as e:
        deployment_logger.error(f"\n💥 Deployment error: {e}")
        exit(1)