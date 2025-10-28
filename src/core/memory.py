import uuid
from datetime import datetime
from typing import Dict, Any, List
import logging
from src.config.config import config
from src.tools.utils import VertexAIFactory, JsonUtils, logger

class ConversationMemoryManager:
    """
    Manages sliding window conversation memory with automatic summarization.
    
    Features:
    - Maintains last 8 detailed conversations
    - Auto-summarizes older conversations when limit reached
    - Builds comprehensive farmer profile over time
    - Provides rich context for agent interactions
    """
    
    def __init__(self):
        self.logger = logging.getLogger('farm_agent.memory')
        self.logger.info("Initializing ConversationMemoryManager with sliding window (8 conversations)")
        
        self.max_detailed_conversations = config.max_detailed_conversations
        self.conversation_history: List[Dict[str, Any]] = []      # Last 8 detailed conversations
        self.summarized_context: str = ""        # Summary of older conversations
        self.farmer_profile: Dict[str, Any] = {             # Accumulated farmer information
            "name": "",
            "location": "",
            "crops": [],
            "farm_size": "",
            "experience": "",
            "interests": [],
            "concerns": [],
            "farming_methods": [],
            "equipment": [],
            "budget_range": ""
        }
        
    def add_conversation(self, query: str, response: str, extracted_context: Dict[str, Any] = None) -> None:
        """
        Add new conversation and manage sliding window memory.
        
        Args:
            query: User's question/request
            response: Agent's response
            extracted_context: Additional context extracted from conversation
        """
        self.logger.debug(f"Adding conversation to memory. Current history size: {len(self.conversation_history)}")
        
        # Create conversation record
        conversation_record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "extracted_info": extracted_context or {}
        }
        
        # Extract and update farmer profile information
        self._extract_farmer_info(query, response, extracted_context)
        
        # Add to conversation history
        self.conversation_history.append(conversation_record)
        
        # Manage sliding window - if we exceed max conversations
        if len(self.conversation_history) > self.max_detailed_conversations:
            self.logger.info(f"Sliding window triggered: {len(self.conversation_history)} conversations exceed max {self.max_detailed_conversations}")
            
            # Summarize oldest conversations before removing
            conversations_to_summarize = self.conversation_history[:-self.max_detailed_conversations]
            self.logger.debug(f"Summarizing {len(conversations_to_summarize)} oldest conversations")
            new_summary = self._summarize_conversations(conversations_to_summarize)
            
            # Update summarized context
            if self.summarized_context:
                self.summarized_context = f"{self.summarized_context}\n\n{new_summary}"
            else:
                self.summarized_context = new_summary
            
            # Keep only last 8 conversations
            self.conversation_history = self.conversation_history[-self.max_detailed_conversations:]
            self.logger.info(f"Memory cleanup complete: kept {len(self.conversation_history)} recent conversations")
            
            logger.info(f"Summarized {len(conversations_to_summarize)} older conversations, maintaining {len(self.conversation_history)} recent ones")
    
    def get_current_context(self) -> Dict[str, Any]:
        """
        Get formatted context for agent injection.
        
        Returns:
            Rich context dictionary with farmer profile, conversation summary, and recent conversations
        """
        
        # Format recent conversations for context
        recent_conversations_text = []
        for i, conv in enumerate(self.conversation_history, 1):
            formatted = f"Q: {conv['query']}\nA: {conv['response'][:200]}{'...' if len(conv['response']) > 200 else ''}"
            recent_conversations_text.append(formatted)
        
        # Build comprehensive context
        context = {
            "farmer_profile": self.farmer_profile,
            "conversation_summary": self.summarized_context if self.summarized_context else "No previous conversation history.",
            "recent_conversations": recent_conversations_text if recent_conversations_text else "No recent conversations.",
            "total_conversations": len(self.conversation_history) + (1 if self.summarized_context else 0),
            "memory_status": f"Tracking {len(self.conversation_history)} recent conversations"
        }
        
        return context
    
    def _extract_farmer_info(self, query: str, response: str, extracted_context: Dict[str, Any] = None) -> None:
        """
        Extract and update farmer profile information from conversations.
        
        Args:
            query: User's question
            response: Agent's response  
            extracted_context: Additional context information
        """
        
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Extract crop information
        crops_mentioned = []
        crop_keywords = {
            'rice': ['rice', 'paddy', 'basmati', 'jasmine rice'],
            'wheat': ['wheat', 'triticum'],
            'cotton': ['cotton', 'kapas'],
            'corn': ['corn', 'maize', 'makka'],
            'soybean': ['soybean', 'soya'],
            'sugarcane': ['sugarcane', 'ganna'],
            'potato': ['potato', 'aloo'],
            'onion': ['onion', 'pyaaz'],
            'tomato': ['tomato', 'tamatar']
        }
        
        for crop, keywords in crop_keywords.items():
            if any(keyword in query_lower or keyword in response_lower for keyword in keywords):
                if crop not in self.farmer_profile['crops']:
                    crops_mentioned.append(crop)
        
        # Update crops in profile
        for crop in crops_mentioned:
            if crop not in self.farmer_profile['crops']:
                self.farmer_profile['crops'].append(crop)
        
        # Extract location information
        location_keywords = ['punjab', 'haryana', 'up', 'uttar pradesh', 'bihar', 'maharashtra', 'gujarat', 'rajasthan', 'karnataka', 'andhra pradesh', 'telangana', 'tamil nadu', 'kerala', 'west bengal', 'odisha', 'madhya pradesh']
        for location in location_keywords:
            if location in query_lower or location in response_lower:
                if not self.farmer_profile['location']:
                    self.farmer_profile['location'] = location.title()
                break
        
        # Extract farm size information
        size_patterns = ['acres', 'acre', 'hectare', 'hectares', 'bigha', 'bighas']
        for word in query.split() + response.split():
            if any(size_word in word.lower() for size_word in size_patterns):
                # Look for numbers before size words
                words = (query + " " + response).split()
                for i, w in enumerate(words):
                    if any(size_word in w.lower() for size_word in size_patterns):
                        # Look for number in previous words
                        for j in range(max(0, i-3), i):
                            if words[j].replace('.', '').replace(',', '').isdigit():
                                if not self.farmer_profile['farm_size']:
                                    self.farmer_profile['farm_size'] = f"{words[j]} {w.lower()}"
                                break
                        break
        
        # Extract farming interests/concerns
        interest_keywords = {
            'organic farming': ['organic', 'chemical-free', 'natural farming'],
            'pest management': ['pest', 'insect', 'disease', 'fungus'],
            'irrigation': ['irrigation', 'water', 'drip', 'sprinkler'],
            'soil health': ['soil', 'fertility', 'nutrients'],
            'market prices': ['price', 'market', 'selling', 'profit'],
            'weather': ['weather', 'rainfall', 'temperature', 'climate']
        }
        
        for interest, keywords in interest_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                if interest not in self.farmer_profile['interests']:
                    self.farmer_profile['interests'].append(interest)
        
        # Extract farming methods mentioned
        method_keywords = {
            'organic': ['organic', 'chemical-free', 'bio'],
            'conventional': ['chemical', 'fertilizer', 'pesticide'],
            'integrated': ['ipm', 'integrated pest management'],
            'precision': ['precision', 'technology', 'sensors']
        }
        
        for method, keywords in method_keywords.items():
            if any(keyword in query_lower or keyword in response_lower for keyword in keywords):
                if method not in self.farmer_profile['farming_methods']:
                    self.farmer_profile['farming_methods'].append(method)
        
        # Update extracted context if provided
        if extracted_context:
            for key, value in extracted_context.items():
                if key == 'crops' and value:
                    for crop in value if isinstance(value, list) else [value]:
                        if crop not in self.farmer_profile['crops']:
                            self.farmer_profile['crops'].append(crop)
                elif key == 'location' and value and not self.farmer_profile['location']:
                    self.farmer_profile['location'] = value
                elif key == 'farm_size' and value and not self.farmer_profile['farm_size']:
                    self.farmer_profile['farm_size'] = value
    
    def _summarize_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """
        Summarize older conversations for long-term memory.
        
        Args:
            conversations: List of conversation records to summarize
            
        Returns:
            Summary text of the conversations
        """
        
        if not conversations:
            return ""
        
        try:
            # Create summarization model
            summary_model = VertexAIFactory.create_model(
                model_name=config.vertexai.model_name,
                system_instruction="""You are a Conversation Summarization Agent for agricultural conversations.

**Your Role:** Create concise, informative summaries of farming conversations that preserve key information for future reference.

**What to Include in Summary:**
- Farmer's crops, location, farm size, and farming interests
- Key agricultural topics discussed (pest management, irrigation, fertilizers, etc.)
- Important decisions or plans made
- Farming challenges or concerns raised
- Methods or techniques discussed
- Any specific recommendations given

**What to Exclude:**
- Detailed technical specifications (keep only key points)
- Repetitive or minor details
- Standard greetings or pleasantries

**Output Format:**
Create a concise paragraph (2-3 sentences) that captures the essence of the farming conversations and the farmer's profile/interests.

**Example:**
"Farmer discussed basmati rice cultivation in Punjab, focusing on organic pest management and irrigation optimization for their 10-acre farm. Key topics included integrated pest management strategies, soil health improvement, and market timing for better prices."
"""
            )
            
            # Prepare conversations for summarization
            conversations_text = ""
            for conv in conversations:
                conversations_text += f"Q: {conv['query']}\nA: {conv['response'][:300]}{'...' if len(conv['response']) > 300 else ''}\n\n"
            
            summarization_prompt = f"""
**CONVERSATIONS TO SUMMARIZE:**

{conversations_text}

**TASK:** Create a concise summary of these agricultural conversations that preserves key farmer information and farming topics discussed. Focus on the farmer's profile, crops, location, farming interests, and main agricultural topics covered.

Keep the summary informative but concise (2-3 sentences maximum)."""
            
            # Generate summary
            response = summary_model.generate_content(summarization_prompt)
            
            if response and response.text:
                summary = response.text.strip()
                logger.info(f"Successfully summarized {len(conversations)} conversations")
                return summary
            else:
                # Fallback summary if AI summarization fails
                topics = set()
                for conv in conversations:
                    if 'pest' in conv['query'].lower():
                        topics.add('pest management')
                    if 'rice' in conv['query'].lower() or 'wheat' in conv['query'].lower():
                        topics.add('crop cultivation')
                    if 'weather' in conv['query'].lower():
                        topics.add('weather planning')
                    if 'price' in conv['query'].lower():
                        topics.add('market analysis')
                
                return f"Farmer engaged in agricultural discussions covering {', '.join(topics) if topics else 'various farming topics'} over {len(conversations)} conversations."
        
        except Exception as e:
            logger.error(f"Error in conversation summarization: {e}")
            # Simple fallback summary
            return f"Previous farming conversations covered various agricultural topics over {len(conversations)} exchanges."
    
    def get_conversation_count(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "recent_conversations": len(self.conversation_history),
            "has_summary": bool(self.summarized_context),
            "total_estimated": len(self.conversation_history) + (8 if self.summarized_context else 0)
        }

class EnhancedSessionManager:
    """
    Manages single persistent sessions with conversation memory throughout user interactions.
    
    Features:
    - Single session per user throughout conversation
    - Integrated conversation memory management
    - Rich context injection for all agent calls
    - Persistent farmer profile building
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # user_id -> session_info
        self.memory_managers: Dict[str, ConversationMemoryManager] = {}  # session_id -> ConversationMemoryManager
        
    async def get_or_create_session(self, user_id: str, runner) -> tuple:
        """
        Get existing session or create new one with memory management.
        
        Args:
            user_id: Unique identifier for the user
            runner: InMemoryRunner instance
            
        Returns:
            Tuple of (session, memory_manager)
        """
        
        if user_id in self.active_sessions:
            # Return existing session and memory manager
            session_info = self.active_sessions[user_id]
            session = session_info['session']
            session_id = session_info['session_id']
            memory_manager = self.memory_managers[session_id]
            logger.info(f"Using existing session {session_id} for user {user_id}")
            return session, memory_manager
        else:
            # Create new session and memory manager
            session_id = str(uuid.uuid4())
            
            try:
                # Properly await the async session creation
                session = await runner.session_service.create_session(
                    app_name=runner.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Create memory manager for this session
                memory_manager = ConversationMemoryManager()
                
                # Store session info
                self.active_sessions[user_id] = {
                    'session': session,
                    'session_id': session_id,
                    'created_at': datetime.now()
                }
                self.memory_managers[session_id] = memory_manager
                
                logger.info(f"Created new session {session_id} for user {user_id}")
                return session, memory_manager
                
            except Exception as e:
                logger.error(f"Failed to create session for user {user_id}: {e}")
                raise
    
    def add_conversation_to_memory(self, session_id: str, query: str, response: str, extracted_context: Dict[str, Any] = None) -> None:
        """
        Add conversation to session memory.
        
        Args:
            session_id: Session identifier
            query: User's query
            response: Agent's response
            extracted_context: Additional context extracted
        """
        
        if session_id in self.memory_managers:
            self.memory_managers[session_id].add_conversation(query, response, extracted_context)
            logger.debug(f"Added conversation to memory for session {session_id}")
        else:
            logger.warning(f"No memory manager found for session {session_id}")
    
    def get_enriched_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get full context for agent injection.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Rich context dictionary for agent use
        """
        
        if session_id in self.memory_managers:
            return self.memory_managers[session_id].get_current_context()
        else:
            # Return empty context if no memory manager
            return {
                "farmer_profile": {},
                "conversation_summary": "No previous conversation history.",
                "recent_conversations": "No recent conversations.",
                "total_conversations": 0,
                "memory_status": "No active memory"
            }
    
    def clear_session(self, user_id: str) -> None:
        """Clear session for user (useful for testing or reset)."""
        if user_id in self.active_sessions:
            session_info = self.active_sessions[user_id]
            session_id = session_info['session_id']
            
            # Clean up
            del self.active_sessions[user_id]
            if session_id in self.memory_managers:
                del self.memory_managers[session_id]
            
            logger.info(f"Cleared session for user {user_id}")

# Initialize enhanced session manager
enhanced_session_manager = EnhancedSessionManager()