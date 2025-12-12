import os
import asyncio
from typing import AsyncGenerator, Generator, Optional, Dict, Any, List

from langchain.chains import LLMChain
from langchain_together import ChatTogether
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.callbacks import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage

from domain.prompts import CHATBOT_PROMPT_TEMPLATE, GREETING_MESSAGES, detect_name_from_input, SUMMARY_PROMPT_TEMPLATE

from domain.session_manager import SessionManager  

class ChatbotService:

    # Agrega estas constantes al inicio de la clase
    BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    MY_ADAPTER = "Jordanqaqqqasdas/chatbot-emocional-v2"
  
    # Inicialización del servicio de chatbot
    def __init__(self, retriever, session_manager):

        self.retriever = retriever               # Configurar el recuperador de documentos
        self.session_manager = session_manager   # Configurar el gestor de sesiones
        self.llm = self._initialize_llm()
    
    
    def _initialize_llm(self):
        print(f"Inicializando modelo: {self.BASE_MODEL}")

        llm = ChatTogether(
            together_api_key=os.getenv("TOGETHER_API_KEY"),
            model=self.BASE_MODEL,
            temperature=0.3,
            max_tokens=350,
        )

        print("Modelo inicializado correctamente")
        return llm

    async def stream_response(self, user_input: str, session_id: str = None) -> AsyncGenerator[str, None]:
        """
        Procesa un mensaje del usuario y genera respuesta en streaming.
        """
        try:
            # Obtener o crear la sesión
            session_id = self.session_manager.get_or_create_session_id(session_id)
            
            # Manejar saludo inicial si es la primera interacción
            if not self.session_manager.has_greeted(session_id):
                name = detect_name_from_input(user_input)
                greeting = GREETING_MESSAGES.get(
                    "welcome_generic", 
                    "¡Hola! ¿En qué puedo ayudarte hoy?"
                )
                if name:
                    greeting = f"¡Hola {name}! ¿En qué puedo ayudarte hoy?"
                self.session_manager.mark_as_greeted(session_id)
                yield greeting
                return
                    
            # Obtener memoria de la sesión
            memory = self.session_manager.get_or_create_memory(session_id)
            
            # Crear cadena de conversación
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                memory=memory,
                combine_docs_chain_kwargs={"prompt": PromptTemplate.from_template(CHATBOT_PROMPT_TEMPLATE)},
                return_source_documents=False
            )
            
            # Generar respuesta en streaming
            response_stream = qa_chain.astream({"question": user_input})
            async for chunk in response_stream:
                if content := chunk.get("answer", ""):
                    yield content
                    
        except Exception as e:
            error_msg = "Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo."
            print(f"Error en stream_response: {e}")
            yield error_msg
        


    # Generacion de resumen de historial por session_id
    def generate_summary(self, chat_history: list) -> str:
        """
        Genera un resumen estructurado del historial de chat usando un prompt de sistema.
        
        Args:
            chat_history (list): Lista de mensajes de la conversación.
            
        Returns:
            str: Resumen formateado.
        """
        try:
            # Convertir el historial a un formato de texto
            formatted_history = "\n".join(
                f"{msg['role'].capitalize()}: {msg['content']}" 
                for msg in chat_history
            )
            
            # Crear el prompt
            prompt = PromptTemplate(
                template=SUMMARY_PROMPT_TEMPLATE,
                input_variables=["chat_history"]
            )
            
            # Crear la cadena de generación
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # Generar el resumen
            summary = chain.run(chat_history=formatted_history)
            
            return summary.strip()
            
        except Exception as e:
            print(f"Error al generar el resumen: {e}")
            return "No se pudo generar el resumen. Por favor, inténtalo de nuevo más tarde."