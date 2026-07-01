import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from brains.config import LLMConfig

# Set up logger
logger = logging.getLogger(__name__)

# Import the Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    SDK_AVAILABLE = True
except ImportError:
    logger.warning("google-genai SDK is not installed. LLM calls will fail until installed.")
    SDK_AVAILABLE = False
    genai = None
    types = None
    APIError = Exception


class TutorResponse(BaseModel):
    """Pydantic model describing the structured tutor JSON schema."""
    answer: str = Field(
        description="The mentor response explaining concepts, asking guiding questions, and pointing the student in the right direction without directly giving the code."
    )
    difficulty: str = Field(
        description="The assessed difficulty level of the concepts being discussed, e.g., Beginner, Intermediate, Advanced."
    )
    concepts: List[str] = Field(
        description="Key programming/architecture concepts touched upon in this answer."
    )
    next_topic: str = Field(
        description="The next recommended topic or exercise the student should tackle to progress."
    )
    memory_to_store: List[str] = Field(
        description="Key observations about the student's understanding, strengths, or weaknesses to store in memory."
    )


class GeminiTutorService:
    """
    Service class responsible for coordinating interactions with the Gemini LLM.
    Handles prompt construction, API communication, and response validation.
    """
    def __init__(self, config: LLMConfig):
        """
        Initializes the Tutor service with a validated configuration.
        
        Args:
            config (LLMConfig): The LLM configuration settings.
        """
        self.config = config
        self._client = None

    @property
    def client(self):
        """Lazy-loaded Google GenAI client instance."""
        if not SDK_AVAILABLE:
            raise RuntimeError("google-genai SDK is not installed. Cannot instantiate client.")
            
        if self._client is None:
            logger.debug("Initializing a new Gemini API Client instance.")
            self._client = genai.Client(api_key=self.config.api_key)
        return self._client

    def build_system_prompt(self, mode: str = "Tutor") -> str:
        """
        Builds the system persona prompt instructing the LLM to behave as a coding mentor.
        
        Args:
            mode (str): The execution mode. Defaults to "Tutor".
            
        Returns:
            str: System instructions prompt.
        """
        system_prompt = (
            "You are an elite Software Engineer and an expert, encouraging programming mentor.\n"
            "Your mission is to guide students to build their coding projects step-by-step.\n\n"
            "Persona & Style Guidelines:\n"
            "1. DO NOT give the final code solution directly. Instead, break concepts down and teach incrementally.\n"
            "2. Encourage debugging. If a student is stuck, ask guiding questions about what they expect vs what is happening.\n"
            "3. Provide clear explanations of concepts with simple, illustrative pseudocode or conceptual examples when helpful.\n"
            "4. Adapt your tone to the student's background based on their profile, history, and memory.\n"
            "5. Keep discussions professional, friendly, and encouraging. Never make a student feel bad for asking questions.\n"
            "6. Never fabricate APIs or libraries. Keep technical details accurate and secure.\n"
            "7. Format code examples clearly and highlight best practices (clean code, error handling, security).\n"
            "8. Focus on understanding: guide them to identify their own bugs so they learn how to debug in the future.\n\n"
            "You must generate output strictly conforming to the requested JSON structure."
        )
        
        if mode.lower() != "tutor":
            logger.info(f"Applying customized tutoring constraints for mode: '{mode}'.")
            
        return system_prompt

    def build_user_prompt(self, user_question: str, student_memory: str, current_project: str) -> str:
        """
        Builds the detailed user session prompt.
        
        Args:
            user_question (str): Student question.
            student_memory (str): Student knowledge and strengths/weaknesses from memory.
            current_project (str): Context of the project currently being built.
            
        Returns:
            str: User interaction prompt.
        """
        q = user_question.strip() if user_question else ""
        mem = student_memory.strip() if student_memory else "No prior history recorded."
        proj = current_project.strip() if current_project else "General practice/No specific project."
        
        user_prompt = (
            "Context of the Student's Session:\n"
            f"--- CURRENT PROJECT: ---\n{proj}\n\n"
            f"--- STUDENT MEMORY / HISTORY: ---\n{mem}\n\n"
            f"--- STUDENT'S QUESTION: ---\n{q}\n\n"
            "Instructions:\n"
            "- Tailor your response based on the student's memory profile (e.g. adjust explanation level, target weak areas, build on strengths).\n"
            "- Formulate a helpful response following the mentor guidelines (guide, don't give the complete solution).\n"
            "- Output the response in JSON matching the specified schema."
        )
        return user_prompt

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Issues a content generation request to the Gemini API.
        
        Args:
            system_prompt (str): System instruction prompt.
            user_prompt (str): User session prompt.
            
        Returns:
            str: Raw JSON string text returned from the model.
        """
        logger.info(f"Issuing Gemini generateContent request utilizing model: {self.config.model_name}")
        
        try:
            response = self.client.models.generate_content(
                model=self.config.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=TutorResponse,
                    temperature=self.config.temperature,
                )
            )
            
            if not response or not response.text:
                logger.error("Empty response returned from Gemini API.")
                raise APIError("Empty response content received.")
                
            return response.text
            
        except APIError as e:
            logger.error(f"Gemini API invocation error: {str(e)}")
            raise RuntimeError(f"Gemini API failure: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to communicate with LLM provider: {str(e)}")
            raise RuntimeError(f"Service communication exception: {str(e)}") from e

    def parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parses the raw JSON string from Gemini, falling back cleanly if fields are absent.
        
        Args:
            raw_response (str): The raw response payload.
            
        Returns:
            Dict[str, Any]: Parsed and validated tutor response dict.
        """
        try:
            data = json.loads(raw_response)
            
            # Defensive check for Pydantic Schema elements
            required_keys = ["answer", "difficulty", "concepts", "next_topic", "memory_to_store"]
            for key in required_keys:
                if key not in data:
                    logger.warning(f"Response JSON missed key '{key}'. Substituting default value.")
                    if key in ["concepts", "memory_to_store"]:
                        data[key] = []
                    elif key == "difficulty":
                        data[key] = "Intermediate"
                    else:
                        data[key] = ""
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Unable to decode response payload as valid JSON. Raw text: '{raw_response}'")
            raise ValueError(f"Tutor response parsing error: {str(e)}") from e

    def tutor(self, user_question: str, student_memory: str, current_project: str, mode: str = "Tutor") -> Dict[str, Any]:
        """
        Coordinates constructing prompts, calling the model, and parsing the response.
        
        Args:
            user_question (str): Student's query.
            student_memory (str): History records of student.
            current_project (str): Context of code project.
            mode (str): Mode selector.
            
        Returns:
            Dict[str, Any]: Structured tutor response dictionary.
        """
        # Validate input inputs
        if not user_question or not user_question.strip():
            logger.warning("Empty user_question provided to tutor service.")
            return {
                "answer": "It looks like your question was empty. What programming concept or bug would you like to explore?",
                "difficulty": "Beginner",
                "concepts": [],
                "next_topic": "Getting Started",
                "memory_to_store": []
            }
            
        system_prompt = self.build_system_prompt(mode)
        user_prompt = self.build_user_prompt(user_question, student_memory, current_project)
        
        raw_text = self.call_llm(system_prompt, user_prompt)
        return self.parse_response(raw_text)


# =====================================================================
# Backward-compatible API wrapper
# =====================================================================
def generate_response(
    user_question: str,
    student_memory: str,
    current_project: str,
    mode: str = "Tutor"
) -> Dict[str, Any]:
    """
    Public entry point module function providing backward compatibility for
    calling code while orchestrating class configurations and defensive catch-alls.
    
    Args:
        user_question (str): Student's question.
        student_memory (str): Prior history.
        current_project (str): Active project file workspace details.
        mode (str): Tutor execution mode.
        
    Returns:
        Dict[str, Any]: Clean parsed dictionary response, never crashes.
    """
    fallback_response = {
        "answer": (
            "I'm sorry, I encountered a connection issue while preparing my response. "
            "Let's review the code together! Could you describe the issue you are facing or share "
            "what you expect the program to do?"
        ),
        "difficulty": "Unknown",
        "concepts": [],
        "next_topic": "Troubleshooting and Diagnostics",
        "memory_to_store": ["Tutor encountered a service timeout or api connection issue."]
    }

    try:
        # Load and validate configuration
        config = LLMConfig()
        config.validate()
        
        # Instantiate and invoke core service
        service = GeminiTutorService(config)
        return service.tutor(user_question, student_memory, current_project, mode)
        
    except ValueError as config_err:
        logger.critical(f"Configuration validation failed: {str(config_err)}")
        fallback_response["answer"] = (
            "The tutoring assistant configuration is incomplete. "
            "Please check that the GEMINI_API_KEY environment variable is correctly set in your environment or .env file."
        )
        return fallback_response
        
    except Exception as e:
        logger.error(f"Tutor service failure encountered: {str(e)}", exc_info=True)
        return fallback_response
