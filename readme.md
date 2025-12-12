# Chatbot Terapéutico con RAG

Este proyecto implementa un chatbot terapéutico usando **FastAPI**, **LangChain**, **FAISS** y un frontend en **React**.  
El backend utiliza RAG (Retrieval Augmented Generation) para dar respuestas empáticas y basadas en fuentes confiables.

##  Instalación y Ejecución 

### 1. Clonar el repositorio
git clone https://github.com/jrdanDp/chatbot-backend.git
### 2. Como ejecutarlo 
- Crea un entorno virtual : 

    python -m venv venv

- Activalo con 

    venv\Scripts\activate

- Instala las dependencias 

    pip install -r requirements.txt

- Ejecuta el proyecto

    uvicorn services.main:app --reload
