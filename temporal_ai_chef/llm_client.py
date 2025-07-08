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
        ingredients_str = ", ".join(ingredients)  # Show all ingredients for better recipe quality
        
        prompt = f"""
You are a professional chef. Create a high-level cooking plan for: {recipe}

Available tools: {tools_str}
Available ingredients: {ingredients_str}

IMPORTANT CONSTRAINTS:
- You can ONLY use ingredients from the available ingredients list above
- Do NOT mention or use any ingredients not in the available list
- All ingredient names must EXACTLY match the available ingredients list
- Create an authentic, traditional version of this recipe using available ingredients

Please provide exactly 4-6 HIGH-LEVEL cooking phases that focus on major cooking techniques:
- Each step should represent ONE major cooking phase or technique
- Assume the robot knows standard prep work (chopping, measuring, basic setup)
- Include essential temperatures and timing for cooking phases
- Focus on the main cooking methods, not detailed micro-instructions
- Ingredient names must EXACTLY match the available ingredients list

Think of this as instructing a skilled robot chef who knows cooking basics but needs the recipe phases.

Format: Return ONLY a numbered list of 4-6 high-level steps, one per line.

Examples of HIGH-LEVEL steps:
❌ Complex: "Preheat oven to 375°F. Slice chicken breasts. Pound to 1/2 inch. Season with salt and pepper."
✅ Simple: "Prepare seasoned chicken cutlets"

❌ Complex: "In bowl 1, mix flour and salt. In bowl 2, beat eggs. In bowl 3, combine breadcrumbs and parmesan. Dredge chicken through all three."
✅ Simple: "Bread the chicken cutlets with flour, egg, and breadcrumb coating"

❌ Complex: "Heat oil in pan. Cook chicken 3-4 minutes per side until golden. Transfer to baking sheet."
✅ Simple: "Pan-fry chicken cutlets until golden brown"
"""

        response = client.chat.completions.create(
            model="gpt-4o",
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
        
        prompt = f"""You are selecting the ONE tool needed to complete this cooking step: "{step}"

Available tools: {tools_str}

DECISION RULES:
1. For PREP work (cutting, slicing, chopping, dicing, preparing) → Use cutting tools (Chef's Knife, Chopping Board, Knife)
2. For MIXING/COMBINING (whisking, beating, mixing, combining, breading) → Use mixing tools (Whisk, Mixing Bowl, Spatula)
3. For COOKING with heat (pan-fry, sauté, fry) → Use Skillet (NOT Stove)
4. For BAKING/ROASTING (bake, roast, heat in oven) → Use Oven
5. For ASSEMBLY/TOPPING (spread, top, assemble) → Use Spatula

Key Examples:
"Prepare seasoned chicken cutlets" → Chef's Knife (preparation = cutting work)
"Bread the chicken cutlets with flour, egg, and breadcrumb coating" → Mixing Bowl (breading = mixing setup)
"Pan-fry chicken cutlets until golden brown" → Skillet (pan-frying = skillet cooking)
"Top cutlets with tomato sauce and mozzarella" → Spatula (topping = assembly work)
"Bake in oven until cheese is melted" → Oven (baking = oven work)

Return ONLY the exact tool name:"""

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


def select_ingredients_with_llm(step: str, ingredients: List[str], plan_context: List[str] = None, step_index: int = 0) -> Optional[List[str]]:
    """Select appropriate ingredients for a cooking step using LLM"""
    client = get_openai_client()
    if not client:
        return None
    
    try:
        ingredients_str = ", ".join(ingredients)
        
        # Build context about previous completed steps only
        context_str = ""
        if plan_context and step_index > 0:
            previous_steps = plan_context[:step_index]  # Only actual previous steps
            context_str = f"""
COOKING CONTEXT:
Steps already completed: {', '.join([f"Step {i+1}: {s}" for i, s in enumerate(previous_steps)])}

Current step being executed: Step {step_index + 1}: {step}

IMPORTANT: Focus ONLY on ingredients used in the current step above. Do not include ingredients from previous steps unless they are specifically mentioned in the current step.
"""
        
        prompt = f"""Identify ONLY the ingredients that are actively used, handled, or manipulated in this specific cooking step: "{step}"
{context_str}
Available ingredients: {ingredients_str}

CRITICAL RULES:
1. ONLY include ingredients explicitly mentioned in THIS step
2. DO NOT include ingredients from previous steps unless they are specifically named in this step  
3. DO NOT assume ingredients are "available" from previous work
4. Focus on what is being done RIGHT NOW in this step

Clear Examples:
"Grill the chicken breasts until fully cooked" → Chicken Breast
"Prepare croutons by tossing bread cubes with olive oil, salt, and black pepper" → Bread, Olive Oil, Salt, Black Pepper  
"Blend together a dressing using Parmesan cheese, garlic, lemon juice, Dijon mustard, olive oil, and salt" → Parmesan, Garlic, Lemon, Dijon Mustard, Olive Oil, Salt
"Toss chopped lettuce with the prepared dressing" → Lettuce
"Assemble the salad by layering the dressed lettuce with sliced grilled chicken, croutons, and additional grated Parmesan cheese" → Parmesan

BAD Examples (what NOT to do):
- If step says "blend dressing with garlic" but mentions bread from previous step → DO NOT include Bread
- If step says "toss lettuce" but doesn't mention chicken → DO NOT include Chicken Breast

Return ONLY ingredients specifically mentioned in this step, separated by commas:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3  # Lower temperature for more consistent selection
        )
        
        if response.choices and response.choices[0].message.content:
            selected_text = response.choices[0].message.content.strip()
            print(f"LLM ingredient selection - Step: '{step}' | LLM Response: '{selected_text}'")
            
            # Parse comma-separated ingredients
            selected_ingredients = [ing.strip() for ing in selected_text.split(',') if ing.strip()]
            print(f"LLM parsed ingredients: {selected_ingredients}")
            
            # Validate that all selected ingredients are in our available ingredients
            valid_ingredients = [ing for ing in selected_ingredients if ing in ingredients]
            invalid_ingredients = [ing for ing in selected_ingredients if ing not in ingredients]
            
            if invalid_ingredients:
                print(f"Warning: Invalid ingredients filtered out: {invalid_ingredients}")
            
            print(f"Final valid ingredients for step: {valid_ingredients}")
            return valid_ingredients if valid_ingredients else None
                
    except Exception as e:
        print(f"LLM ingredient selection failed: {e}")
        return None