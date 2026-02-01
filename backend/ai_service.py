"""
AI Service for handling Ollama interactions
"""

import httpx
from typing import AsyncGenerator, Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3:8b"

# Improved Greek system prompt - Natural, clear, professional tone with memory command handling
SYSTEM_PROMPT = """Είμαι ο AI Mentor. Βοηθάω με ερωτήσεις, προβλήματα και συζητήσεις.

Απαντώ:
- Με σαφήνεια και ακρίβεια
- Σε απλά ελληνικά
- Σύντομα όταν γίνεται, αναλυτικά όταν χρειάζεται

Αποφεύγω:
- Περιττές εισαγωγές
- Επαναλήψεις
- Υπερβολικές εκφράσεις

Το ύφος μου είναι σταθερό, σοβαρό και φιλικό.

ΧΕΙΡΙΣΜΟΣ ΕΝΤΟΛΩΝ ΜΝΗΜΗΣ:

1. Όταν ο χρήστης δίνει εντολή αποθήκευσης (π.χ. "Θυμήσου ότι...", "Το όνομά μου είναι...", "Λέγομαι...", "Με λένε..."):
   → Απάντηση: "✅ Αποθηκεύτηκε στη μνήμη μου"
   → ΜΗΝ επαναλάβεις την αποθηκευμένη τιμή
   → ΜΗΝ πεις "Σε λένε [όνομα]" ή παρόμοια

2. Όταν ο χρήστης διορθώνει πληροφορία (π.χ. "Όχι, είμαι...", "Διόρθωσε...", "Άλλαξε..."):
   → Απάντηση: "✅ Διορθώθηκε στη μνήμη μου"
   → ΜΗΝ επαναλάβεις τη νέα τιμή
   → ΜΗΝ πεις "Εντάξει, τώρα σε λένε [όνομα]" ή παρόμοια

3. Όταν ο χρήστης ρωτά για αποθηκευμένη πληροφορία (π.χ. "Πώς με λένε;", "Τι θυμάσαι;", "Ποιο είναι το όνομά μου;"):
   → Απάντηση: [τιμή από τη μνήμη]
   → Απάντησε φυσικά (π.χ. "Σε λένε Σάκης")

ΣΗΜΑΝΤΙΚΟ: Ξεχώρισε ΑΠΟΘΗΚΕΥΣΗ από ΑΝΑΚΤΗΣΗ. Μην τις μπερδεύεις ποτέ.

Παραδείγματα:

Χρήστης: "Θυμήσου ότι το όνομά μου είναι Σάκης"
Εσύ: "✅ Αποθηκεύτηκε στη μνήμη μου"

Χρήστης: "Όχι, λέγομαι Νίκος"
Εσύ: "✅ Διορθώθηκε στη μνήμη μου"

Χρήστης: "Πώς με λένε;"
Εσύ: "Σε λένε Νίκος"

Χρήστης: "Θυμήσου ότι μου αρέσει το ποδόσφαιρο"
Εσύ: "✅ Αποθηκεύτηκε στη μνήμη μου"

Χρήστης: "Τι μου αρέσει;"
Εσύ: "Σου αρέσει το ποδόσφαιρο"
"""


class AIService:
    """Service for interacting with Ollama AI"""
    
    def __init__(self):
        self.ollama_url = OLLAMA_BASE_URL
        self.default_model = MODEL_NAME
        self.current_model = MODEL_NAME
        self.streaming_enabled = True
        logger.info(f"AIService initialized with model: {self.default_model}")
    
    async def check_ollama_status(self) -> bool:
        """Check if Ollama service is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    
                    # Check if default model exists
                    if self.default_model in model_names:
                        self.current_model = self.default_model
                        logger.info(f"Using model: {self.current_model}")
                    elif model_names:
                        self.current_model = model_names[0]
                        logger.warning(f"Default model {self.default_model} not found, using: {self.current_model}")
                    
                    return True
                return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def warm_up(self) -> bool:
        """Warm up the model with a lightweight request"""
        try:
            logger.info(f"Warming up model: {self.current_model}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.current_model,
                        "prompt": "Hello",
                        "stream": False,
                        "options": {
                            "num_predict": 10
                        }
                    }
                )
                if response.status_code == 200:
                    logger.info("Model warm-up successful")
                    return True
                logger.warning(f"Warm-up returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Warm-up failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            "model": self.current_model,
            "streaming_enabled": self.streaming_enabled,
            "ollama_url": self.ollama_url
        }
    
    async def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        use_online: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response from Ollama"""
        try:
            # Build prompt with system message
            full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            full_messages.extend(messages)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.current_model,
                        "messages": full_messages,
                        "stream": True
                    }
                ) as response:
                    if response.status_code != 200:
                        yield {
                            "error": f"Ollama returned status {response.status_code}",
                            "done": True
                        }
                        return
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                
                                if "message" in data and "content" in data["message"]:
                                    yield {
                                        "token": data["message"]["content"],
                                        "done": data.get('done', False)
                                    }
                                
                                if data.get('done'):
                                    yield {
                                        "done": True,
                                        "metrics": {}
                                    }
                                    break
                            except json.JSONDecodeError:
                                continue
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {
                "error": str(e),
                "done": True
            }
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        use_online: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate response (non-streaming fallback)"""
        try:
            # Build prompt with system message
            full_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            full_messages.extend(messages)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.current_model,
                        "messages": full_messages,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = ""
                    if "message" in data and "content" in data["message"]:
                        content = data["message"]["content"]
                    
                    return {
                        "content": content,
                        "thinking_state": None,
                        "used_online": use_online
                    }
                else:
                    return {
                        "content": f"Error: Ollama returned status {response.status_code}",
                        "thinking_state": None,
                        "used_online": False
                    }
        
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return {
                "content": f"Error generating response: {str(e)}",
                "thinking_state": None,
                "used_online": False
            }
    
    async def generate_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate a summary of the conversation"""
        try:
            summary_prompt = "Summarize the following conversation concisely:\n\n"
            for msg in messages[-10:]:  # Last 10 messages
                summary_prompt += f"{msg['role']}: {msg['content']}\n"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.current_model,
                        "prompt": summary_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 150,
                            "temperature": 0.5
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', 'Summary generation failed')
                
                return "Summary generation failed"
        
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return f"Error: {str(e)}"


# Global AI service instance
ai_service = AIService()