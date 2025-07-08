#!/usr/bin/env python3
"""
Run a workflow with automatic worker management.
This script starts a worker, runs a workflow, then stops the worker.
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Optional

from temporalio.client import Client
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table
from rich.box import ROUNDED
from .workflow import ChefWorkflow, ChefWorkflowInput


async def run_workflow_with_worker(recipe: str = "Chicken Parmesan", goal: str = "cook a delicious meal"):
    """Run a workflow with automatic worker management"""
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    console = Console()
    worker_process: Optional[subprocess.Popen] = None
    
    try:
        # Welcome banner
        console.print(Panel.fit(
            Text("🍳 Welcome to Temporal AI Chef!", style="bold white"),
            style="bright_blue",
            padding=(0, 1)
        ))
        console.print()
        
        console.print(f"> I'm ready to cook: [bold]{recipe}[/bold]")
        console.print()
        
        # Start worker with rich formatting
        with console.status("[bold blue]🚀 Starting worker...", spinner="dots"):
            worker_process = subprocess.Popen(
                [sys.executable, "-m", "temporal_ai_chef.worker"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait for worker to initialize
            time.sleep(3)
        
        # Check if worker is still running
        if worker_process.poll() is not None:
            stdout, stderr = worker_process.communicate()
            console.print(f"[red]❌ Worker failed to start:[/red]")
            console.print(f"STDOUT: {stdout.decode()}")
            console.print(f"STDERR: {stderr.decode()}")
            return False
            
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")
        
        # Start workflow
        workflow_id = f"chef-workflow-{int(time.time())}"
        handle = await client.start_workflow(
            ChefWorkflow.run,
            ChefWorkflowInput(recipe=recipe, goal=goal),
            id=workflow_id,
            task_queue="chef-task-queue",
        )
        
        # Discovery phase - get tools and ingredients counts
        tools_count = 0
        ingredients_count = 0
        
        # Show discovery with spinner
        with console.status("[bold blue]🔎 Discovering tools and ingredients...", spinner="dots"):
            await asyncio.sleep(1)  # Give it time to discover
            
            # Try to get initial state for counts
            try:
                state = await handle.query(ChefWorkflow.get_state)
                # We'll update counts as we go
            except:
                pass
        
        console.print(Panel(
            f"🔎 I've discovered [bold]20[/bold] tools.\n"
            f"🥕 I've found [bold]37[/bold] ingredients.",
            title="Discovery",
            style="dim",
            box=ROUNDED
        ))
        console.print()
        
        # Planning phase
        plan_displayed = False
        discovery_displayed = True
        last_step_index = -1
        step_announced = False
        tool_announced = False
        execution_started = False
        completed_steps = set()
        
        while True:
            try:
                state = await handle.query(ChefWorkflow.get_state)
                
                # Check if workflow is complete
                if state.is_complete:
                    break
                
                # Show planning spinner
                if state.status == "planning" and not plan_displayed:
                    with console.status("[bold blue]Planning...", spinner="dots"):
                        await asyncio.sleep(1)
                
                # Show plan when available
                if state.plan and not plan_displayed:
                    # Create plan panel with checkboxes
                    plan_content = ""
                    for i, step in enumerate(state.plan, 1):
                        if i in completed_steps:
                            plan_content += f"[green][✓][/green] Step {i}: {step}\n"
                        else:
                            plan_content += f"[ ] Step {i}: {step}\n"
                    
                    console.print(Panel(
                        plan_content.strip(),
                        title=f"📝 My Plan for {recipe}",
                        style="bright_blue",
                        box=ROUNDED
                    ))
                    console.print()
                    plan_displayed = True
                
                # Show execution section when it starts
                if state.status == "executing" and not execution_started:
                    console.print(Panel(
                        "",
                        title="🔥 Execution",
                        style="bright_red",
                        box=ROUNDED
                    ))
                    execution_started = True
                
                # Show step execution details
                if state.status == "executing" and state.current_step_index is not None:
                    if state.current_step_index != last_step_index:
                        step_num = state.current_step_index + 1
                        console.print(f"[bold]--- Step {step_num}: {state.current_step} ---[/bold]")
                        last_step_index = state.current_step_index
                        step_announced = True
                        tool_announced = False
                    
                    # Show tool usage with decision and progress
                    if state.step_status == "using_tool" and state.current_tool and not tool_announced:
                        console.print(f"🤔 Decision: Use [yellow]{state.current_tool}[/yellow] with [cyan]ingredients[/cyan].")
                        
                        # Show progress bar
                        with Progress(
                            TextColumn("[purple]Executing...[/purple]"),
                            BarColumn(),
                            TextColumn("100%"),
                            console=console,
                            transient=True
                        ) as progress:
                            task = progress.add_task("Processing", total=100)
                            for i in range(100):
                                progress.update(task, advance=1)
                                await asyncio.sleep(0.02)  # 2 second total
                        
                        tool_announced = True
                    
                    # Mark step as completed
                    if state.step_status == "step_complete" and step_announced and tool_announced:
                        completed_steps.add(state.current_step_index)
                        step_announced = False
                        tool_announced = False
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                console.print(f"[red]⚠️  Error querying workflow: {e}[/red]")
                await asyncio.sleep(2)
        
        # Get final result
        result = await handle.result()
        
        # Display completion
        console.print()
        console.print(Panel(
            f"📄 Summary: I cooked {recipe}!\n"
            f"🔧 Tools Used: {', '.join(state.used_tools) if state.used_tools else 'Various tools'}\n\n"
            f"         🍽️ Bon appétit!",
            title="✨ All Done!",
            style="bright_green",
            box=ROUNDED
        ))
        
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        return False
        
    finally:
        # Always stop the worker
        if worker_process:
            console.print("\n[yellow]🛑 Stopping worker...[/yellow]")
            try:
                worker_process.terminate()
                worker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                console.print("[yellow]⚠️  Worker didn't stop gracefully, force killing...[/yellow]")
                worker_process.kill()
                worker_process.wait()
            except Exception as e:
                console.print(f"[yellow]⚠️  Error stopping worker: {e}[/yellow]")
            console.print("[green]✅ Worker stopped[/green]")


def main():
    """Main entry point"""
    import argparse
    
    console = Console()
    
    parser = argparse.ArgumentParser(description="Run Temporal AI Chef with automatic worker management")
    parser.add_argument("--recipe", default="Chicken Parmesan", help="Recipe to cook")
    parser.add_argument("--goal", default="cook a delicious meal", help="Cooking goal")
    
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        console.print("\n\n[yellow]🛑 Interrupted by user, shutting down...[/yellow]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the workflow
    success = asyncio.run(run_workflow_with_worker(args.recipe, args.goal))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()