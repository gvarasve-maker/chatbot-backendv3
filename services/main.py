import json
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Importaciones de las nuevas clases de servicio y dominio
from domain.chatbot import ChatbotService
from domain.session_manager import SessionManager
from data.rag_loader import RAGSystem
from services.email_service import send_summary_email

# -- Modelos de Datos (Pydantic) --

class ChatMessage(BaseModel):
    """Modelo de mensaje del usuario"""
    user_input: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None

    @validator('user_input')
    def validate_user_input(cls, v):
        """Valida que el mensaje no esté vacío (solo espacios)"""
        if not v or not v.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return v.strip()

class SummaryRequest(BaseModel):
    session_id: str
    email: str


# -- Ciclo de Vida de la Aplicación --

# Diccionario para mantener las instancias de los servicios
service_instances = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Inicializa los servicios al arrancar y los limpia al apagar.
    """
    print("Iniciando servicios...")
    # 1. Inicializar el sistema RAG
    rag_system = RAGSystem()
    rag_system.setup()
    
    # 2. Inicializar el gestor de sesiones
    session_manager = SessionManager()
    
    # 3. Inicializar el servicio de chatbot 
    chatbot_service = ChatbotService(
            retriever=rag_system.get_retriever(),
            session_manager=session_manager
    )
    
    # Almacenar instancias para ser usadas por los endpoints
    service_instances['chatbot_service'] = chatbot_service
    service_instances['session_manager'] = session_manager 
    print("Servicios listos.")
    
    yield
    
    # Código de limpieza al apagar (si fuera necesario)
    service_instances.clear()
    print("Servicios detenidos.")


# -- Inicialización de la App FastAPI --

app = FastAPI(
    title="Chatbot Emocional API",
    description="API para chatbot de apoyo emocional con arquitectura por capas.",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Endpoints de la API --

@app.get("/health")
async def health_check():

    return {"status": "healthy", "version": app.version}


@app.post("/chat/stream")
async def chat_stream_endpoint(request: Request, message: ChatMessage):
   
    chatbot_service = service_instances.get('chatbot_service')
    if not chatbot_service:
        raise HTTPException(status_code=503, detail="Servicio no disponible.")
        
    # Obtener o crear session_id
    session_id = chatbot_service.session_manager.get_or_create_session_id(message.session_id)
    accept_header = request.headers.get("accept", "")

    async def generate_sse_events():
        """Generador asíncrono para la respuesta en streaming (SSE)."""
        try:
            async for chunk in chatbot_service.stream_response(message.user_input, session_id):
                yield f"data: {json.dumps({'message': chunk})}\n\n"
        except Exception as e:
            error_message = f"Error en el stream: {e}"
            yield f"data: {json.dumps({'error': error_message})}\n\n"
    
    if "text/event-stream" in accept_header:
        # Respuesta con Server-Sent Events
        return StreamingResponse(
            generate_sse_events(),
            media_type="text/event-stream",
            headers={
                "x-session-id": session_id,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    else:
        # Respuesta JSON completa
        try:
            full_response = "".join([
                chunk async for chunk in chatbot_service.stream_response(message.user_input, session_id)
            ])
            return JSONResponse(
                content={
                    "message": full_response,
                    "session_id": session_id
                },
                headers={"x-session-id": session_id}
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e),
                headers={"x-session-id": session_id}
            )


@app.post("/summary")
async def create_summary(request: SummaryRequest):
    try:

        session_manager = service_instances.get('session_manager')
        if not session_manager:
            raise HTTPException(status_code=500, detail="Error interno del servidor")
        
        # 1. Obtener el historial de la sesión
        history = session_manager.get_history(request.session_id)
        if not history:
            raise HTTPException(status_code=404, detail="No se encontró historial para la sesión")
        
        # 2. Generar el resumen
        chatbot_service = service_instances.get('chatbot_service')
        if not chatbot_service:
            raise HTTPException(status_code=500, detail="Error interno del servidor")
        
        summary = chatbot_service.generate_summary(history)
        
        # 3. Enviar el correo
        if not send_summary_email(request.email, summary):
            raise HTTPException(status_code=500, detail="Error al enviar el correo")
        
        return {"message": "Resumen enviado exitosamente"}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))