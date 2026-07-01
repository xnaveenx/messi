import os
import asyncio
import cognee
from dotenv import load_dotenv

load_dotenv()

async def initialize_memory():
    await cognee.forget(everything=True)
  
    print("Local Cognee setup complete!")

async def add_memory(user_input: str):

    print(f" Remembering: {user_input}")
    
    await cognee.remember(user_input)
    return "Memory saved successfully."

async def fetch_memory(query: str) -> str:
    print(f"Recalling context for: {query}")
    search_results = await cognee.recall(query)


    if not search_results:
        return "No relevant past context found."
    context_string = "\n".join(map(str, search_results))
    return context_string


async def test_run():
    await initialize_memory()
    test_struggle = "User struggles with writing python for loops and often forgets the colon."
    await add_memory(test_struggle)
  
    new_question = "How do i iterate over a list?"
    retrieved_context = await fetch_memory(new_question)

    print(" \nResults")
    print(f"Context given to LLM: {retrieved_context}")

if __name__ == "__main__":
    asyncio.run(test_run())
