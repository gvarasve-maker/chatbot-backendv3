import uuid
from typing import Optional, Dict, Any
from langchain.memory import ConversationBufferWindowMemory

# Gestor de sesiones de usuario para el chatbot
class SessionManager:

    def __init__(self):

        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session_id(self, session_id: Optional[str] = None) -> str:
        """Recupera un ID de sesión existente o genera uno nuevo si no se proporciona."""
        return session_id if session_id else str(uuid.uuid4())

    def _get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Recupera o crea la estructura de datos de la sesión para un ID dado."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "memory": ConversationBufferWindowMemory(
                    k=4,
                    ai_prefix="Asistente",
                    human_prefix="Usuario",
                    memory_key="chat_history",
                    return_messages=True
                ),
                "name": None,
                "greeted": False
            }
        return self.sessions[session_id]
    def get_or_create_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Recupera o crea la memoria de conversación para una sesión."""
        session = self._get_or_create_session(session_id)
        return session["memory"]    

    def clear_session(self, session_id: str) -> None:
        """Elimina todos los datos asociados a una sesión."""
        self.sessions.pop(session_id, None)
    
    def save_name(self, session_id: str, name: str) -> None:
        """Guarda el nombre del usuario para una sesión."""
        session = self._get_or_create_session(session_id)
        session["name"] = name
    
    def get_name(self, session_id: str) -> Optional[str]:
        """Recupera el nombre del usuario de una sesión, si existe."""
        if session_id in self.sessions:
            return self.sessions[session_id].get("name")
        return None

    def has_name(self, session_id: str) -> bool:
        """Verifica si se ha guardado un nombre para la sesión."""
        return session_id in self.sessions and self.sessions[session_id].get("name") is not None

    def has_greeted(self, session_id: str) -> bool:
        """Verifica si el usuario de la sesión ya ha sido saludado."""
        return session_id in self.sessions and self.sessions[session_id].get("greeted", False)
    
    def mark_as_greeted(self, session_id: str) -> None:
        """Marca al usuario de una sesión como saludado."""
        session = self._get_or_create_session(session_id)
        session["greeted"] = True

    def get_history(self, session_id: str) -> Optional[list]:
        """
        Obtiene el historial de mensajes de una sesión.
        
        Args:
            session_id (str): ID de la sesión.
            
        Returns:
            Optional[list]: Lista de mensajes en formato de diccionario o None si la sesión no existe.
        """
        if session_id not in self.sessions:
            return None
            
        memory = self.sessions[session_id]["memory"]
        messages = memory.chat_memory.messages
        
        # Convertir los mensajes a un formato de diccionario
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                role = "user" if msg.type == "human" else "assistant"
                formatted_messages.append({"role": role, "content": msg.content})
        
        return formatted_messages