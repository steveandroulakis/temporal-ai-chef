import asyncio
import uuid
from datetime import datetime
from temporalio.client import Client
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.emoji import Emoji
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.spinner import Spinner
from rich.columns import Columns
from rich.box import HEAVY
from .workflow import ChefWorkflow, ChefWorkflowInput


async def main():
    """Main CLI entry point for Temporal AI Chef"""
    console = Console()
    
    # Welcome banner
    console.print(Panel.fit(
        Text("🍳 Welcome to Temporal AI Chef!", style="bold white"),
        style="bright_blue",
        padding=(0, 1)
    ))
    console.print()
    
    # Get recipe from user
    recipe = console.input("[bold]> I'm ready to cook:[/bold] ").strip()
    
    if not recipe:
        console.print("[red]❌ Please enter a recipe![/red]")
        return
    
    try:
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")
        
        # Create unique workflow ID
        workflow_id = f"chef-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Start the workflow
        handle = await client.start_workflow(
            ChefWorkflow.run,
            ChefWorkflowInput(recipe=recipe),
            id=workflow_id,
            task_queue="chef-task-queue"
        )
        
        # Poll workflow state and display real-time updates
        last_status = None
        last_step_index = -1
        last_step_status = None
        plan_displayed = False
        discovery_displayed = False
        ready_confirmed = False
        step_announced = False
        tool_announced = False
        execution_started = False
        completed_steps = set()
        step_progress = {}
        
        while True:
            try:
                # Query current state
                state = await handle.query(ChefWorkflow.get_state)
                
                # Show discovery section
                if state.status == "planning" and not discovery_displayed:
                    # Get tools and ingredients count from state
                    tools_count = len(state.used_tools) if state.used_tools else 0
                    ingredients_count = 0  # Will be populated when we have ingredient data
                    
                    console.print()
                    console.print(Panel(
                        f"🔎 I've discovered {tools_count or 'several'} tools.\n"
                        f"🥕 I've found {ingredients_count or 'various'} ingredients.",
                        title="Discovery",
                        style="dim"
                    ))
                    discovery_displayed = True
                
                # Show planning spinner
                if state.status == "planning" and not plan_displayed:
                    console.print()
                    with console.status("[bold blue]Planning...", spinner="dots"):
                        await asyncio.sleep(1)  # Show spinner briefly
                
                # Display plan when available
                if state.plan and not plan_displayed:
                    console.print()
                    
                    # Create plan panel with checkboxes
                    plan_content = ""
                    for i, step in enumerate(state.plan, 1):
                        if i <= len(state.completed_steps):
                            plan_content += f"[✓] Step {i}: {step}\n"
                        else:
                            plan_content += f"[ ] Step {i}: {step}\n"
                    
                    console.print(Panel(
                        plan_content.strip(),
                        title=f"📝 My Plan for {recipe}",
                        style="bright_blue"
                    ))
                    plan_displayed = True
                    
                    # Ask if ready to proceed
                    console.print()
                    console.input("[bold]Ready to start cooking? Press Enter to begin...[/bold]")
                    ready_confirmed = True
                
                # Show execution section
                if state.status == "executing" and ready_confirmed and not execution_started:
                    console.print()
                    console.print(Panel(
                        "",
                        title="🔥 Execution",
                        style="bright_red"
                    ))
                    execution_started = True
                
                # Show step execution details
                if state.status == "executing" and state.current_step and state.current_step_index != last_step_index:
                    step_num = state.current_step_index + 1
                    console.print(f"\n[bold]--- Step {step_num}: {state.current_step} ---[/bold]")
                    last_step_index = state.current_step_index
                    step_announced = True
                    tool_announced = False
                    # Brief pause to let user read the step
                    await asyncio.sleep(2.4)
                
                # Show tool usage with decision
                if state.step_status == "using_tool" and state.current_tool and not tool_announced:
                    ingredients_text = ", ".join(state.current_ingredients) if state.current_ingredients else "ingredients"
                    console.print(f"🤔 Decision: Use [yellow]{state.current_tool}[/yellow] with [cyan]{ingredients_text}[/cyan].")
                    
                    # Show execution status and wait for the actual activity to complete
                    with console.status("[purple]Executing...[/purple]", spinner="dots"):
                        # Wait for the step to complete (the actual use_tool activity takes 0.5-3 seconds)
                        while state.step_status == "using_tool":
                            await asyncio.sleep(0.3)
                            try:
                                state = await handle.query(ChefWorkflow.get_state)
                            except:
                                break
                    
                    tool_announced = True
                
                # Show step completion
                if state.step_status == "step_complete" and step_announced and tool_announced:
                    completed_steps.add(state.current_step_index)
                    step_announced = False
                    tool_announced = False
                    # Brief pause before moving to next step
                    await asyncio.sleep(1.5)
                
                # Check if workflow is complete
                if state.is_complete:
                    break
                
                # Wait before next poll
                await asyncio.sleep(0.5)  # Poll more frequently for better UX
                
            except Exception as e:
                console.print(f"[red]⚠️  Error querying workflow: {e}[/red]")
                await asyncio.sleep(2)
        
        # Wait for final result
        result = await handle.result()
        
        # Display completion
        console.print("\n")
        console.print(Panel(
            f"📄 Summary: I cooked {recipe}!\n"
            f"🔧 Tools Used: {', '.join(state.used_tools) if state.used_tools else 'Various tools'}\n"
            f"🥕 Ingredients Used: {', '.join(state.used_ingredients) if state.used_ingredients else 'Various ingredients'}\n\n"
            f"         🍽️ Bon appétit!",
            title="✨ All Done!",
            style="bright_green"
        ))
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Cooking interrupted by user![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        console.print("[dim]💡 Make sure the Temporal server is running and worker.py is started![/dim]")


def main_sync():
    """Synchronous entry point for console script"""
    asyncio.run(main())

if __name__ == "__main__":
    main_sync()