# Tool functions that the bot can use to perform specific tasks
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
    """Returns a Wikipedia summary for the given topic."""
    try:
        # Fetch Wikipedia REST API for the search query
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
    """Evaluates a mathematical expression and returns the numeric result."""
    try:
        import math
        # Load all math module functions (sin, cos, sqrt, pi, etc.)
        math_funcs = {k: v for k, v in vars(math).items() if not k.startswith("_")}
        # Safely evaluate the expression using simple_eval (prevents code injection)
        result = simple_eval(expression, functions=math_funcs)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool(approval_mode="never_require")
def analizar_texto(
    text: Annotated[str, Field(description="Text to analyze: word count, vowels, palindrome detection, reversal")]
) -> str:
    """Counts words/characters/vowels, detects palindromes, and reverses the given text."""
    # Count non-empty words by splitting on whitespace
    palabras = len([w for w in text.strip().split() if w])
    # Count all characters including spaces and punctuation
    caracteres = len(text)
    # Count vowels including Spanish accented versions (á, é, í, ó, ú, ü)
    vocales = len(re.findall(r"[aeiouáéíóúü]", text, re.IGNORECASE))
    # Reverse the entire text
    invertido = text[::-1]
    # Remove punctuation and spaces, convert to lowercase for palindrome check
    limpio = re.sub(r"[^a-z0-9]", "", text.lower())
    # Check if cleaned text reads the same forwards and backwards
    es_palindromo = limpio == limpio[::-1]
    palindromo_str = " — ¡ES PALÍNDROMO!" if es_palindromo else ""
    # Create a summary showing first 40 chars and main stats
    resumen = f"'{text[:40]}' -> {palabras} palabras, {caracteres} chars, {vocales} vocales{palindromo_str}"
    # Return results as JSON for the bot to parse
    return (
        f'{{"palabras": {palabras}, "caracteres": {caracteres}, "vocales": {vocales}, '
        f'"invertido": "{invertido}", "esPalindromo": {str(es_palindromo).lower()}, '
        f'"resumen": "{resumen}"}}'
    )


@tool(approval_mode="never_require")
def dato_random_de_internet() -> str:
    """Fetches a random curious fact from the internet."""
    try:
        # Call Cat Facts API to get a random interesting fact
        r = httpx.get("https://catfact.ninja/fact", timeout=10)
        if r.is_success:
            data = r.json()
            # Escape quotes in the fact text to prevent JSON parsing issues
            fact = data["fact"].replace('"', '\\"')
            return f'{{"dato": "{fact}", "fuente": "catfact.ninja"}}'
        return "No se pudo obtener el dato."
    except Exception as e:
        return f"Error fetching fact: {e}"
