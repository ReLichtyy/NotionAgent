import os
import json
from typing import Dict, Any
from clients.openai_client import OpenAIAppClient
from core.logger import get_logger

logger = get_logger("LocalAnalyzer")

class LocalProjectAnalyzer:
    def __init__(self, openai_client: OpenAIAppClient):
        self.openai_client = openai_client

    def analyze_directory(self, path: str) -> str:
        """
        Scans a local directory for key configuration and architecture files,
        reads them, and uses the LLM to generate a structured analysis 
        (architecture, risks, tech debt).
        """
        if not os.path.isdir(path):
            return f"Error: La ruta '{path}' no es un directorio válido."
            
        key_files = ["package.json", "pyproject.toml", "requirements.txt", "go.mod", 
                     "docker-compose.yml", "README.md", ".env.example", "tsconfig.json"]
                     
        collected_data = {}
        
        # 1. Collect Key Files
        for root, _, files in os.walk(path):
            for file in files:
                if file in key_files:
                    full_path = os.path.join(root, file)
                    # To avoid massive reads, only read root-level or shallow files
                    depth = full_path.replace(path, "").count(os.sep)
                    if depth < 3:
                        try:
                            with open(full_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                # Truncate very long files (e.g. huge READMEs or package-locks if accidentally matched)
                                collected_data[file] = content[:3000]
                        except Exception as e:
                            logger.warning(f"Could not read {file}: {e}")

        if not collected_data:
            return "No se encontraron archivos de configuración o documentación clave para analizar el proyecto."

        # 2. Build Prompt for LLM inference
        data_str = ""
        for name, content in collected_data.items():
            data_str += f"\n--- Archivo: {name} ---\n{content}\n"

        prompt = f"""
Eres un 'Local Project Analyzer' experto en arquitectura de software.
He extraído los archivos clave de configuración y documentación de un proyecto local.
Tu objetivo es transformar esto en un Resumen Ejecutivo Técnico útil para el workspace del usuario, SIN volcar código crudo innecesario.

Archivos extraídos:
{data_str}

Genera un reporte estructurado en Markdown que incluya:
1. Propósito del Proyecto (Inferencia basada en dependencias/README)
2. Stack Técnico y Arquitectura (Frontend, Backend, Monorepo, BDs)
3. Riesgos Técnicos y Deuda Técnica visible
4. Oportunidades de Mejora
5. Siguientes pasos (Backlog sugerido)

Sé analítico, maduro y no repitas cosas obvias. Solo devuelve el reporte en Markdown.
"""
        try:
            logger.info(f"Analyzing local project at {path}...")
            response = self.openai_client.chat([{"role": "system", "content": prompt}], model="gpt-4o-mini")
            if response and response.content:
                return response.content
        except Exception as e:
            logger.error(f"Failed to analyze local project: {e}")
            return f"Error al analizar el proyecto local: {e}"
            
        return "No se pudo generar el análisis."
