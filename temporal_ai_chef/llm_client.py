"""
LLM client module for OpenAI integration.
This module is imported conditionally to avoid workflow sandbox restrictions.
"""

import os
from typing import List, Optional


def get_openai_client():
    """Get OpenAI client if available"""
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return OpenAI(api_key=api_key)
    except ImportError:
        pass
    return None


def generate_plan_with_llm(recipe: str, tools: List[str], ingredients: List[str]) -> Optional[List[str]]:
    """Generate cooking plan using LLM"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        # Create comprehensive prompt for plan generation
        tools_str = ", ".join(tools)
        ingredients_str = ", ".join(ingredients[:10])  # Limit to prevent token overflow
        
        prompt = f"""
You are a professional chef. Create a simplified step-by-step cooking plan for: {recipe}

Available tools: {tools_str}
Available ingredients: {ingredients_str}

Please provide exactly 3-5 clear, concise cooking steps that include:
- Essential steps only (no detailed prep work)
- Specific temperatures when relevant (e.g., 375°F, 450°F)
- Basic timing (e.g., 15 minutes, 3 minutes per side)
- Simple, actionable instructions

Format: Return ONLY a numbered list of 3-5 steps, one per line.
Example:
1. Preheat oven to 375°F and prepare baking sheet
2. Season and bread the chicken pieces
3. Bake for 20-25 minutes until golden
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content.strip()
            # Parse the numbered list into individual steps
            steps = []
            for line in content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering (e.g., "1. " or "- ")
                    step = line.split('.', 1)[-1].strip() if '.' in line else line.lstrip('- ').strip()
                    if step:
                        steps.append(step)
            return steps if steps else None
            
    except Exception as e:
        print(f"LLM plan generation failed: {e}")
        return None


def select_tool_with_llm(step: str, tools: List[str]) -> Optional[str]:
    """Select appropriate tool for a cooking step using LLM"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        tools_str = ", ".join(tools)
        
        prompt = f"""
You are a professional chef. For this cooking step: "{step}"

Available tools: {tools_str}

Select the MOST appropriate tool from the available tools. Respond with ONLY the exact tool name from the list.

Examples:
Step: "Chop the onions into small pieces" → Chopping Board
Step: "Mix the ingredients in a large bowl" → Mixing Bowl
Step: "Bake for 25 minutes" → Oven

Tool name only:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.3  # Lower temperature for more consistent tool selection
        )
        
        if response.choices and response.choices[0].message.content:
            selected_tool = response.choices[0].message.content.strip()
            # Validate that the selected tool is in our available tools
            if selected_tool in tools:
                return selected_tool
                
    except Exception as e:
        print(f"LLM tool selection failed: {e}")
        return None


def select_ingredients_with_llm(step: str, ingredients: List[str]) -> Optional[List[str]]:
    """Select appropriate ingredients for a cooking step using LLM"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        ingredients_str = ", ".join(ingredients)
        
        prompt = f"""
You are a professional chef. For this cooking step: "{step}"

Available ingredients: {ingredients_str}

Select the MOST appropriate ingredients from the available ingredients that would be used in this step. Respond with ONLY the ingredient names from the list, separated by commas.

Examples:
Step: "Whisk eggs with milk and vanilla" → Eggs, Milk, Vanilla Extract
Step: "Season the chicken with salt and pepper" → Chicken Breast, Salt, Black Pepper
Step: "Serve with maple syrup" → Maple Syrup

Ingredient names only (comma-separated):"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3  # Lower temperature for more consistent selection
        )
        
        if response.choices and response.choices[0].message.content:
            selected_text = response.choices[0].message.content.strip()
            # Parse comma-separated ingredients
            selected_ingredients = [ing.strip() for ing in selected_text.split(',') if ing.strip()]
            # Validate that all selected ingredients are in our available ingredients
            valid_ingredients = [ing for ing in selected_ingredients if ing in ingredients]
            return valid_ingredients if valid_ingredients else None
                
    except Exception as e:
        print(f"LLM ingredient selection failed: {e}")
        return None