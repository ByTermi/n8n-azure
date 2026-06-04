# Funciones de herramientas que el bot puede usar para realizar tareas específicas
import re
from typing import Annotated

import httpx
from agent_framework import tool
from pydantic import Field
from simpleeval import simple_eval


@tool(approval_mode="never_require")
def wikipedia_search(
    query: Annotated[str, Field(description="Topic or question to search on Wikipedia")]
) -> str:
    """Retorna un resumen de Wikipedia para el tema dado."""
    try:
        # Obtiene datos de la API REST de Wikipedia para la búsqueda
        r = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}",
            follow_redirects=True,
            timeout=10,
            headers={"User-Agent": "CompaChucho/1.0 (educational chatbot; contact@example.com)"},
        )
        if r.is_success:
            data = r.json()
            return data.get("extract", "No summary found.")
        return f"Wikipedia error: {r.status_code}"
    except Exception as e:
        return f"Error searching Wikipedia: {e}"


@tool(approval_mode="never_require")
def calculator(
    expression: Annotated[str, Field(description="Valid math expression, e.g. '2 + 2' or 'sqrt(16)'")]
) -> str:
    """Evalúa una expresión matemática y retorna el resultado numérico."""
    try:
        import math
        # Carga todas las funciones del módulo math (sin, cos, sqrt, pi, etc.)
        math_funcs = {k: v for k, v in vars(math).items() if not k.startswith("_")}
        # Evalúa la expresión de forma segura usando simple_eval (previene inyección de código)
        result = simple_eval(expression, functions=math_funcs)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool(approval_mode="never_require")
def analizar_texto(
    text: Annotated[str, Field(description="Text to analyze: word count, vowels, palindrome detection, reversal")]
) -> str:
    """Cuenta palabras/caracteres/vocales, detecta palíndromos e invierte el texto dado."""
    # Cuenta palabras no vacías dividiendo por espacios en blanco
    palabras = len([w for w in text.strip().split() if w])
    # Cuenta todos los caracteres incluyendo espacios y puntuación
    caracteres = len(text)
    # Cuenta vocales incluyendo versiones acentuadas de español (á, é, í, ó, ú, ü)
    vocales = len(re.findall(r"[aeiouáéíóúü]", text, re.IGNORECASE))
    # Invierte el texto completo
    invertido = text[::-1]
    # Elimina puntuación y espacios, convierte a minúsculas para verificar palíndromo
    limpio = re.sub(r"[^a-z0-9]", "", text.lower())
    # Verifica si el texto limpio se lee igual hacia adelante y hacia atrás
    es_palindromo = limpio == limpio[::-1]
    palindromo_str = " — ¡ES PALÍNDROMO!" if es_palindromo else ""
    # Crea un resumen mostrando los primeros 40 caracteres y estadísticas principales
    resumen = f"'{text[:40]}' -> {palabras} palabras, {caracteres} chars, {vocales} vocales{palindromo_str}"
    # Retorna resultados como JSON para que el bot los procese
    return (
        f'{{"palabras": {palabras}, "caracteres": {caracteres}, "vocales": {vocales}, '
        f'"invertido": "{invertido}", "esPalindromo": {str(es_palindromo).lower()}, '
        f'"resumen": "{resumen}"}}'
    )


@tool(approval_mode="never_require")
def dato_random_de_internet() -> str:
    """Obtiene un dato curioso aleatorio de internet."""
    try:
        # Llama a la API de Datos Felinos para obtener un dato interesante aleatorio
        r = httpx.get("https://catfact.ninja/fact", timeout=10)
        if r.is_success:
            data = r.json()
            # Escapa las comillas en el texto para prevenir problemas de parseo JSON
            fact = data["fact"].replace('"', '\\"')
            return f'{{"dato": "{fact}", "fuente": "catfact.ninja"}}'
        return "No se pudo obtener el dato."
    except Exception as e:
        return f"Error fetching fact: {e}"
