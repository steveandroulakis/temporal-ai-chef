import json
import os
import time
import random
from typing import List
from dataclasses import dataclass

from temporalio import activity


@dataclass
class ToolUsageInput:
    tool_name: str
    ingredients: List[str]
    step_description: str


@dataclass
class PlanInput:
    goal: str
    recipe: str
    tools: List[str]
    ingredients: List[str]


@dataclass
class ToolSelectionInput:
    step: str
    tools: List[str]


@dataclass
class IngredientsSelectionInput:
    step: str
    ingredients: List[str]
    plan_context: List[str] = None
    step_index: int = 0


class ChefActivities:
    """Activities for chef workflow execution."""

    @activity.defn
    async def get_tools(self) -> List[str]:
        """Load available tools from tools.json"""
        activity.logger.info("Loading available tools")
        
        tools_path = os.path.join(os.path.dirname(__file__), "data", "tools.json")
        with open(tools_path, 'r') as f:
            tools = json.load(f)
        
        activity.logger.info(f"Loaded {len(tools)} tools")
        return tools

    @activity.defn
    async def get_ingredients(self) -> List[str]:
        """Load available ingredients from ingredients.json"""
        activity.logger.info("Loading available ingredients")
        
        ingredients_path = os.path.join(os.path.dirname(__file__), "data", "ingredients.json")
        with open(ingredients_path, 'r') as f:
            ingredients = json.load(f)
        
        activity.logger.info(f"Loaded {len(ingredients)} ingredients")
        return ingredients

    @activity.defn
    async def use_tool(self, input: ToolUsageInput) -> str:
        """Simulate using a tool with a random delay"""
        activity.logger.info(f"Using tool: {input.tool_name} for step: {input.step_description}")
        
        # Simulate work with random delay (1.5 to 9 seconds)
        delay = random.uniform(1.0, 2.0)
        time.sleep(delay)
        
        result = f"Successfully used {input.tool_name} for: {input.step_description}"
        activity.logger.info(result)
        return result

    @activity.defn
    async def get_plan(self, input: PlanInput) -> List[str]:
        """Generate cooking plan using OpenAI LLM"""
        activity.logger.info(f"Generating plan for: {input.recipe}")
        
        # Try LLM first, fall back to mock if not available
        try:
            from .llm_client import generate_plan_with_llm
            llm_plan = generate_plan_with_llm(input.recipe, input.tools, input.ingredients)
            
            if llm_plan:
                activity.logger.info(f"Generated {len(llm_plan)} steps using LLM")
                return llm_plan
            else:
                activity.logger.warning("LLM plan generation failed, using mock plan")
                return self._get_mock_plan(input.recipe)
                
        except Exception as e:
            activity.logger.warning(f"LLM plan generation failed: {e}, using mock plan")
            return self._get_mock_plan(input.recipe)
    
    def _get_mock_plan(self, recipe: str) -> List[str]:
        """Fallback mock plan generation (3-5 steps)"""
        if "chicken parm" in recipe.lower() or "chicken parmesan" in recipe.lower():
            return [
                "Pound and bread the chicken",
                "Pan-fry until golden brown",
                "Assemble with sauce and cheese",
                "Bake until cheese melts"
            ]
        elif "pasta" in recipe.lower():
            return [
                "Boil pasta in salted water",
                "Prepare the sauce",
                "Combine pasta with sauce",
                "Serve with cheese"
            ]
        elif "toast" in recipe.lower():
            return [
                "Whisk eggs with milk and spices",
                "Dip bread slices in mixture",
                "Cook in buttered skillet until golden",
                "Serve with syrup"
            ]
        else:
            return [
                "Prepare ingredients",
                "Cook main components",
                "Combine and finish",
                "Serve hot"
            ]

    @activity.defn
    async def get_tool_for_step(self, input: ToolSelectionInput) -> str:
        """Determine which tool to use for a step using OpenAI LLM"""
        activity.logger.info(f"Determining tool for step: {input.step}")
        
        # Try LLM first, fall back to mock if not available
        try:
            from .llm_client import select_tool_with_llm
            selected_tool = select_tool_with_llm(input.step, input.tools)
            
            if selected_tool:
                activity.logger.info(f"Selected tool using LLM: {selected_tool}")
                return selected_tool
            else:
                activity.logger.warning("LLM tool selection failed, using mock selection")
                return self._get_mock_tool(input.step)
                
        except Exception as e:
            activity.logger.warning(f"LLM tool selection failed: {e}, using mock selection")
            return self._get_mock_tool(input.step)
    
    def _get_mock_tool(self, step: str) -> str:
        """Fallback mock tool selection"""
        step_lower = step.lower()
        
        if "pound" in step_lower or "chop" in step_lower or "cut" in step_lower:
            return "Chopping Board"
        elif "bread" in step_lower or "mix" in step_lower or "combine" in step_lower:
            return "Mixing Bowl"
        elif "pan-fry" in step_lower or "fry" in step_lower or "saute" in step_lower:
            return "Skillet"
        elif "bake" in step_lower or "roast" in step_lower:
            return "Oven"
        elif "boil" in step_lower or "simmer" in step_lower:
            return "Saucepan"
        elif "drain" in step_lower or "strain" in step_lower:
            return "Strainer"
        else:
            # Default to a versatile tool
            return "Spatula"

    @activity.defn
    async def get_ingredients_for_step(self, input: IngredientsSelectionInput) -> List[str]:
        """Determine which ingredients to use for a step using OpenAI LLM"""
        activity.logger.info(f"Determining ingredients for step: {input.step}")
        
        # Try LLM first, fall back to mock if not available
        try:
            from .llm_client import select_ingredients_with_llm
            activity.logger.info(f"Calling LLM for step: '{input.step}' with context: step_index={input.step_index}")
            selected_ingredients = select_ingredients_with_llm(
                input.step, 
                input.ingredients, 
                input.plan_context, 
                input.step_index
            )
            
            if selected_ingredients:
                activity.logger.info(f"LLM returned ingredients: {selected_ingredients}")
                return selected_ingredients
            else:
                activity.logger.warning("LLM returned no ingredients, using mock selection")
                return self._get_mock_ingredients(input.step)
                
        except Exception as e:
            activity.logger.error(f"LLM ingredients selection failed with error: {e}, using mock selection")
            return self._get_mock_ingredients(input.step)
    
    def _get_mock_ingredients(self, step: str) -> List[str]:
        """Fallback mock ingredients selection"""
        step_lower = step.lower()
        
        if "chicken" in step_lower:
            return ["Chicken Breast", "Salt", "Black Pepper"]
        elif "pasta" in step_lower or "boil" in step_lower:
            return ["Pasta", "Salt", "Water"]
        elif "sauce" in step_lower:
            return ["Tomato Sauce", "Garlic", "Onion"]
        elif "cheese" in step_lower:
            return ["Parmesan Cheese", "Mozzarella Cheese"]
        elif "bread" in step_lower:
            return ["Breadcrumbs", "Flour", "Eggs"]
        elif "toast" in step_lower:
            return ["Bread", "Eggs", "Milk", "Butter"]
        else:
            # Default to basic ingredients
            return []