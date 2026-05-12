"""
agent_service.py
────────────────
Responsible for ONE thing only:
Creating and running the LangChain agent.

It does NOT know about:
- HTTP requests (that's routes/chat.py)
- Session memory (that's memory_service.py)
- How results are stored (that's session_store.py)

It only knows:
- How to create the LLM
- How to create the agent with tools
- How to run the agent with a message + history
"""

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage
from core.config import settings
from core.constants import SYSTEM_PROMPT
from tools.drive_search import drive_search_tool


class AgentService:
    """
    Handles everything related to the LangChain agent.
    
    Why a class and not just functions?
    - The LLM client is created ONCE and reused (expensive to recreate)
    - The prompt template is created ONCE and reused
    - The tools list is created ONCE and reused
    - Only the AgentExecutor is created per request (because it holds
      per-request state like scratchpad)
    
   
    """

    def __init__(self):
        # These are created ONCE when the service starts
        # Not on every request — that would be slow
        self._llm = self._create_llm()
        self._tools = self._create_tools()
        self._prompt = self._create_prompt()

    # ── Private setup methods ─────────────────────────────────────

    def _create_llm(self) -> ChatGroq:
        """
        Creates the LLM client.
        
        Why ChatGroq specifically?
        - ChatGroq is a LangChain-compatible wrapper around Groq's API
        - LangChain needs its own wrapper classes (ChatGroq, ChatOpenAI, 
          ChatGoogleGenerativeAI) to work with tool calling
        - You can't pass a raw OpenAI/Groq client directly to LangChain
        
        Why read from settings and not hardcode?
        - If you want to switch from llama3-70b to mixtral, 
          you change ONE line in .env, not in code
        - In production, different environments can use different models
          (e.g., cheaper model in staging, better model in production)
        """
        return ChatGroq(
            model=settings.llm_model,              # from .env
            api_key=settings.groq_api_key,          # from .env
            temperature=settings.llm_temperature,   # from .env
        )

    def _create_tools(self) -> list:
        """
        Returns the list of tools the agent can use.
        
        Why a list?
        - LangChain agents can have MULTIPLE tools
        - Right now we have one (drive_search_tool)
        - Tomorrow you might add: drive_download_tool, drive_preview_tool
        - Adding a new tool = just append to this list
        - The agent automatically learns about new tools from their docstrings
        
        Why not create tools here?
        - Tools are defined in tools/drive_search.py (single responsibility)
        - This service just USES them, not defines them
        - Same reason controllers don't define database schemas
        """
        return [drive_search_tool]

    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Creates the prompt template.
        
        Why ChatPromptTemplate?
        LangChain's prompt template is not just a string — it's a 
        structured format that the agent executor knows how to fill:
        
        Template slots:
        ┌─────────────────────────────────────────────┐
        │ SystemMessage(SYSTEM_PROMPT)                 │ ← Fixed instructions
        │ MessagesPlaceholder("chat_history")          │ ← Filled with history
        │ HumanMessage("{input}")                      │ ← Filled with user msg
        │ MessagesPlaceholder("agent_scratchpad")      │ ← Filled by LangChain
        └─────────────────────────────────────────────┘
        
        What is agent_scratchpad?
        When the agent decides to use a tool, LangChain needs somewhere
        to store the intermediate steps:
        
        Step 1: LLM says "I'll call drive_search_tool"
                → stored in scratchpad
        Step 2: Tool runs, returns results
                → stored in scratchpad  
        Step 3: LLM reads scratchpad, composes final answer
        
        Without scratchpad, the agent can't do multi-step reasoning.
        It's like a notepad the agent uses while thinking.
        
        Why is SYSTEM_PROMPT in constants.py not here?
        - System prompt is a constant, not logic
        - Keeping it in constants.py means you can update the prompt
          without touching service logic
        - Also easier to read — this file stays focused on structure
        """
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    # ── Private agent creation ─────────────────────────────────────

    def _create_executor(self) -> AgentExecutor:
        """
        Creates a fresh AgentExecutor for each request.
        
        Why fresh per request and not reused like LLM/prompt/tools?
        
        AgentExecutor holds the "scratchpad" — the intermediate
        reasoning steps for ONE conversation turn. If you reused it:
        
        User1: "find PDFs"
               → scratchpad: [called drive_search, got results...]
        User2: "find images"  
               → scratchpad still has User1's steps! Wrong behavior.
        
        LLM, prompt, tools are STATELESS — same for everyone.
        AgentExecutor is STATEFUL per request — must be fresh.
        
        This is equivalent to creating a new Express req/res handler
        per request vs sharing state between requests.
        
        AgentExecutor parameters explained:
        
        verbose=True:
            Prints every reasoning step to console.
            In development, you see exactly what the agent is thinking:
            > Entering new AgentExecutor chain...
            > Invoking: drive_search_tool with query="mimeType='application/pdf'"
            > Found 3 files...
            > Final Answer: I found 3 PDF files...
            Set to False in production (logs get noisy).
        
        max_iterations=5:
            The agent runs in a loop. Without a limit:
            Agent calls tool → reads result → calls tool again → ...forever
            5 iterations is enough for complex queries.
            Prevents infinite loops from LLM confusion.
        
        handle_parsing_errors=True:
            Sometimes the LLM outputs malformed JSON for tool calls.
            Instead of crashing, LangChain retries with an error message.
            Like a try/catch around the entire agent loop.
        """
        agent = create_tool_calling_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=self._prompt,
        )

        return AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=settings.debug_mode,       # True in dev, False in prod
            max_iterations=10,
            handle_parsing_errors=True,
            return_intermediate_steps=False,    # Don't expose tool calls to user
        )

    # ── Public method — called by ChatService ──────────────────────

    async def run(
        self,
        message: str,
        history: list[BaseMessage],
    ) -> str:
        """
        Runs the agent with a user message and conversation history.
        
        Args:
            message: The user's current natural language query
            history: Full conversation history from MemoryService
                     List of HumanMessage and AIMessage objects
        
        Returns:
            The agent's final response as a plain string
        
        Why async?
        - FastAPI is async
        - The agent makes HTTP calls to Groq API and Google Drive API
        - Making them async means other users aren't blocked while
          one user's request is in flight
        - Without async: User1 waits for Drive → User2 blocked
        - With async: User1 waits for Drive → User2 gets served
        
        Why is history passed IN instead of fetched here?
        - AgentService doesn't know about sessions or storage
        - ChatService fetches history from MemoryService
        - Then passes it here
        - This makes AgentService completely testable in isolation:
          test_agent_service.py can pass fake history directly
          without needing a real session store
        """
        executor = self._create_executor()

        try:
            result = await executor.ainvoke({   # ainvoke = async invoke
                "input": message,
                "chat_history": history,
            })
            return result.get("output", "I couldn't generate a response. Please try again.")

        except Exception as e:
            # Don't let agent errors crash the entire request
            # Log it and return a user-friendly message
            print(f"[AgentService] Error running agent: {e}")
            return (
                "I encountered an error while searching. "
                "Please try rephrasing your request."
            )