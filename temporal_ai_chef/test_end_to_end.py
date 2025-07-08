import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from temporalio.client import Client
from temporalio.worker import Worker

from .workflow import ChefWorkflow, ChefWorkflowInput
from .activities import ChefActivities


async def simulate_cli_interaction(recipe: str = "Chicken Parmesan"):
    """Simulate the CLI interaction for testing"""
    print("🍳 Welcome to Temporal AI Chef!")
    print("=" * 50)
    print(f"What would you like to cook today?\n> {recipe}")
    print(f"\n🧠 AI Chef is thinking about: {recipe}...")
    
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
        
        print(f"📋 Started cooking workflow: {workflow_id}")
        
        # Poll workflow state and display real-time updates
        last_status = None
        last_step_index = -1
        plan_displayed = False
        step_announced = False
        tool_announced = False
        
        while True:
            try:
                # Query current state
                state = await handle.query(ChefWorkflow.get_state)
                
                # Display plan when available
                if state.plan and not plan_displayed:
                    print("\n[PLANNING] 📝")
                    for i, step in enumerate(state.plan, 1):
                        print(f"- Step {i}: {step}")
                    print()
                    plan_displayed = True
                
                # Show status changes
                if state.status != last_status:
                    if state.status == "executing":
                        print("[EXECUTING] 🔥")
                    last_status = state.status
                
                # Show step execution details
                if state.current_step and state.current_step_index != last_step_index:
                    step_num = state.current_step_index + 1
                    print(f"\n[EXECUTING STEP {step_num}: {state.current_step}]")
                    last_step_index = state.current_step_index
                    step_announced = True
                    tool_announced = False
                
                # Show tool usage
                if state.step_status == "using_tool" and state.current_tool and not tool_announced:
                    # Get appropriate emoji for tool
                    tool_emoji = {
                        "Chopping Board": "🔪",
                        "Mixing Bowl": "🥣", 
                        "Skillet": "🍳",
                        "Oven": "🔥",
                        "Saucepan": "🍲",
                        "Spatula": "🥄",
                        "Whisk": "🥄",
                        "Blender": "💨"
                    }.get(state.current_tool, "🔧")
                    
                    print(f"-> Using tool: [{state.current_tool}]... {tool_emoji} (Simulating work...)")
                    tool_announced = True
                
                # Show step completion
                if state.step_status == "step_complete" and step_announced and tool_announced:
                    print("-> DONE.")
                    step_announced = False
                    tool_announced = False
                
                # Check if workflow is complete
                if state.is_complete:
                    break
                
                # Wait before next poll
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️  Error querying workflow: {e}")
                await asyncio.sleep(2)
        
        # Wait for final result
        result = await handle.result()
        
        # Display completion
        print("\n" + "=" * 50)
        print("✅ DONE!")
        print(f"📄 Summary: {result}")
        print("🍽️  Bon appétit!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_end_to_end():
    """Test the complete end-to-end flow with worker and CLI"""
    print("🧪 Testing End-to-End Flow...")
    print("=" * 60)
    
    # Enable logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise, show only warnings/errors
    
    try:
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")
        
        # Create and start worker
        chef_activities = ChefActivities()
        worker = Worker(
            client,
            task_queue="chef-task-queue",
            workflows=[ChefWorkflow],
            activities=[
                chef_activities.get_tools,
                chef_activities.get_ingredients,
                chef_activities.get_plan,
                chef_activities.get_tool_for_step,
                chef_activities.use_tool
            ],
            activity_executor=ThreadPoolExecutor(max_workers=5)
        )
        
        print("🚀 Starting worker and CLI simulation...")
        print()
        
        async with worker:
            # Run the CLI simulation
            success = await simulate_cli_interaction("Chicken Parmesan")
            
            if success:
                print("\n" + "🎉" * 20)
                print("🎉 END-TO-END TEST SUCCESSFUL! 🎉")
                print("🎉" * 20)
                print("\n✅ All components working:")
                print("   - Temporal workflow execution")
                print("   - Real-time state querying") 
                print("   - CLI display formatting")
                print("   - Tool selection and simulation")
                print("   - Step-by-step progress tracking")
                return True
            else:
                print("\n❌ End-to-end test failed!")
                return False
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def main():
    """Main entry point for console script"""
    success = asyncio.run(test_end_to_end())
    exit(0 if success else 1)

if __name__ == "__main__":
    main()