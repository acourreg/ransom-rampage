from app.config import settings
from app.storage.redis_store import init_redis, close_redis
from app.storage.vector_store import vectorstore
import asyncio

# Lazy singletons
_redis = None
_vectorstore = None
_llm = None
_ciso_graph = None
_sre_graph = None
_byte_graph = None

async def startup():
    global _redis, _vectorstore, _llm, _ciso_graph, _sre_graph, _byte_graph
    
    # Init Redis
    await init_redis(settings.REDIS_URL)
    from app.storage.redis_store import _redis
    
    # Init FAISS vectorstore
    _vectorstore = vectorstore

    # Init LLM
    from langchain_openai import ChatOpenAI
    _llm = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)
    
    from app.core.agents import ciso_graph, sre_graph, byte_graph
    _ciso_graph = ciso_graph
    _sre_graph = sre_graph
    _byte_graph = byte_graph
    print("✅ Bootstrap complete: Redis, FAISS, LLM, agent graphs initialized")

async def shutdown():
    from app.storage.redis_store import close_redis
    await close_redis()
    print("✅ Bootstrap shutdown: Redis closed")

def get_redis():
    from app.storage.redis_store import _redis
    return _redis

def get_vectorstore():
    from app.storage.vector_store import vectorstore as get_vectorstore
    return get_vectorstore()

def get_llm():
    from langchain_openai import ChatOpenAI
    from app.config import settings
    return ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY)

def get_ciso_graph():
    # Will import from app.core.agents.ciso_graph once refactored
    pass

def get_sre_graph():
    # Will import from app.core.agents.sre_graph once refactored
    pass

def get_byte_graph():
    # Will import from app.core.agents.byte_graph once refactored
    pass