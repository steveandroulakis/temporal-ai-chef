import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from temporalio import workflow

from .activities import (
    ChefActivities,
    ToolUsageInput,
    PlanInput,
    ToolSelectionInput,
    IngredientsSelectionInput
)


@dataclass
class ChefWorkflowInput:
    recipe: str
    goal: str = "Create a step-by-step cooking plan"


@dataclass
class WorkflowState:
    recipe: str
    plan: List[str]
    current_step: Optional[str]
    current_step_index: int
    completed_steps: List[str]
    used_tools: List[str]
    current_tool: Optional[str]
    used_ingredients: List[str]
    current_ingredients: List[str]
    step_tools: List[str]  # Tool used for each step (index matches step index)
    step_ingredients: List[List[str]]  # Ingredients used for each step
    current_tool_result: Optional[str]  # Result from current tool usage
    is_complete: bool
    status: str  # "planning", "executing", "completed"
    step_status: str  # "selecting_tool", "using_tool", "step_complete"


@workflow.defn
class ChefWorkflow:
    def __init__(self) -> None:
        self._state = WorkflowState(
            recipe="",
            plan=[],
            current_step=None,
            current_step_index=0,
            completed_steps=[],
            used_tools=[],
            current_tool=None,
            used_ingredients=[],
            current_ingredients=[],
            step_tools=[],
            step_ingredients=[],
            current_tool_result=None,
            is_complete=False,
            status="planning",
            step_status=""
        )

    @workflow.run
    async def run(self, input: ChefWorkflowInput) -> str:
        self._state.recipe = input.recipe
        self._state.status = "planning"
        
        workflow.logger.info(f"Starting chef workflow for: {input.recipe}")
        
        # Create activities instance
        chef_activities = ChefActivities()
        
        # Get available tools and ingredients
        tools = await workflow.execute_activity_method(
            chef_activities.get_tools,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        ingredients = await workflow.execute_activity_method(
            chef_activities.get_ingredients,
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        # Generate the cooking plan
        plan_input = PlanInput(
            goal=input.goal,
            recipe=input.recipe,
            tools=tools,
            ingredients=ingredients
        )
        plan = await workflow.execute_activity_method(
            chef_activities.get_plan,
            plan_input,
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        self._state.plan = plan
        self._state.status = "executing"
        
        workflow.logger.info(f"Generated plan with {len(plan)} steps")
        
        # Execute each step in the plan
        for i, step in enumerate(plan):
            self._state.current_step = step
            self._state.current_step_index = i
            self._state.step_status = "selecting_tool"
            
            # Determine which tool to use for this step
            tool_selection_input = ToolSelectionInput(
                step=step,
                tools=tools
            )
            tool = await workflow.execute_activity_method(
                chef_activities.get_tool_for_step,
                tool_selection_input,
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            # Update state with selected tool
            self._state.current_tool = tool
            
            # Determine which ingredients to use for this step
            ingredients_selection_input = IngredientsSelectionInput(
                step=step,
                ingredients=ingredients,
                plan_context=plan,
                step_index=i
            )
            step_ingredients = await workflow.execute_activity_method(
                chef_activities.get_ingredients_for_step,
                ingredients_selection_input,
                start_to_close_timeout=timedelta(seconds=10)
            )
            
            # Update state with selected ingredients
            self._state.current_ingredients = step_ingredients
            self._state.step_status = "using_tool"
            
            # Brief pause to allow CLI to show tool selection
            await asyncio.sleep(2)
            
            # Use the tool
            tool_input = ToolUsageInput(
                tool_name=tool,
                ingredients=ingredients,
                step_description=step
            )
            
            tool_result = await workflow.execute_activity_method(
                chef_activities.use_tool,
                tool_input,
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            # Store the tool usage result in state
            self._state.current_tool_result = tool_result
            
            # Update state - step completed
            self._state.step_status = "step_complete"
            self._state.completed_steps.append(step)
            if tool not in self._state.used_tools:
                self._state.used_tools.append(tool)
            
            # Track tool and ingredients used for this specific step
            self._state.step_tools.append(tool)
            self._state.step_ingredients.append(step_ingredients)
            
            # Track used ingredients
            for ingredient in step_ingredients:
                if ingredient not in self._state.used_ingredients:
                    self._state.used_ingredients.append(ingredient)
        
        # Mark as complete
        self._state.current_step = None
        self._state.current_tool = None
        self._state.current_ingredients = []
        self._state.current_tool_result = None
        self._state.is_complete = True
        self._state.status = "completed"
        self._state.step_status = ""
        
        summary = f"Cooked {input.recipe} using {', '.join(self._state.used_tools)}"
        workflow.logger.info(f"Workflow complete: {summary}")
        
        return summary

    @workflow.query
    def get_state(self) -> WorkflowState:
        """Query method to get current workflow state"""
        return self._state