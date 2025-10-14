# 🌾 AI Farm Management Assistant

**Advanced AI-powered farming assistant with production-grade architecture, memory management, and sequential planning capabilities.**

## 🏗️ Project Structure (Refactored)

```
FARM_AGENT/
├── src/                        # Root for all source code
│   ├── __init__.py
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── agents.py           # Agent implementations
│   │   ├── callbacks.py        # Callback logic
│   │   ├── guardrails.py       # Guardrail rules and checks
│   │   ├── memory.py           # Memory management
│   │   ├── planning.py         # Planning agents
│   │   └── processors.py       # Data processing logic
│   ├── tools/                  # Reusable tools and utilities
│   │   ├── __init__.py
│   │   ├── tools.py            # Tool definitions (weather, market, etc.)
│   │   └── utils.py            # Shared helper functions
│   ├── config/                 # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration loading
│   │   ├── .env                # Environment variables
│   │   └── env.example         # Example environment file
│   ├── observability/          # Monitoring and logging
│   │   ├── __init__.py
│   │   ├── logging_setup.py    # Logging configuration
│   │   └── observability.py    # Observability metrics/tracing
│   └── models/                 # Data models
│       ├── __init__.py
│       └── models.py
├── main.py                     # Application entry point
├── pyproject.toml              # Project configuration
├── README.md                   # This file
├── LICENSE                     # License information
├── ARCHITECTURE.md             # Architecture documentation
└── OBSERVABILITY.md            # Observability documentation
```

## 🚀 Features

- **🧠 Memory Management**: Sliding window conversation memory with farmer profile building
- **🎯 Sequential Planning**: Production-grade planning with quality assurance and reflection
- **🛡️ Guardrails**: Agricultural domain enforcement and safety checks
- **🌤️ Weather Integration**: Real-time weather data and forecasts
- **💰 Market Prices**: Live mandi prices for agricultural commodities
- **📊 Data Processing**: Google Sheets integration for customer data
- **🌾 RAG Knowledge**: Agricultural knowledge base with vector search
- **📈 Observability**: Laminar tracing for performance monitoring
- **🔄 Session Management**: Persistent conversations across interactions

## 🏃‍♂️ Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd farm_agent
   ```

2. **Configure Environment**:
   ```bash
   # Copy environment template
   cp src/config/env.example src/config/.env
   
   # Edit with your credentials
   nano src/config/.env
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Assistant**:
   ```bash
   python main.py
   ```

## 🔧 Configuration

The system uses environment variables for configuration. Key settings:

- `PROJECT_ID`: Google Cloud Project ID
- `LOCATION`: Google Cloud region (e.g., us-east4)  
- `MODEL`: Gemini model name (default: gemini-2.0-flash-001)
- `RAG_CORPUS_NAME`: RAG corpus resource name
- `LMNR_PROJECT_API_KEY`: Laminar observability API key (optional)
- `SHEETS_BASE_URL`: Google Sheets API endpoint

## 🎯 Usage Examples

### Sequential Planning Queries
```
"Create a complete plan to manage pest outbreak in my cotton field"
"How do I convert 5 acres from rice to organic vegetable farming?"
"Step-by-step process for setting up drip irrigation system"
```

### Information Queries
```
"What's the weather forecast for Punjab?"
"Current market prices for basmati rice"
"Show me customer data for ID: 12345"
"Best practices for organic pest management"
```

## 🏛️ Architecture Highlights

- **Modular Design**: Clean separation of concerns with src/ structure
- **Memory System**: ConversationMemoryManager with sliding window + summarization
- **Planning Intelligence**: Sequential planning with quality reflection
- **Safety First**: Multi-layer guardrails and input validation
- **Production Ready**: Comprehensive error handling and resource cleanup

## 📝 Development

The new structure provides clear separation:

- **Core Logic** (`src/core/`): Business logic, agents, memory, planning
- **Tools & Utils** (`src/tools/`): Reusable components and utilities  
- **Configuration** (`src/config/`): All configuration and environment management
- **Models** (`src/models/`): Data models and schemas
- **Observability** (`src/observability/`): Logging, tracing, monitoring

## 🛠️ Technical Stack

- **AI Framework**: Google ADK (Agent Development Kit)
- **LLM**: Google Gemini 2.0 Flash
- **Memory**: Production-grade conversation management
- **Planning**: Producer-Critic reflection pattern
- **Observability**: Laminar tracing integration
- **Data**: Pydantic models with validation

## 📚 Documentation

- [Architecture Guide](ARCHITECTURE.md)
- [Observability Setup](OBSERVABILITY.md)
- [API Documentation](docs/api.md)

---

**Built with ❤️ for farmers, powered by Google ADK and production-grade AI patterns.**