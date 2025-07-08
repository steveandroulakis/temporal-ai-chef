import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from workflow import ChefWorkflow, ChefWorkflowInput
from activities import ChefActivities


async def test_complete_workflow():
    """Test complete workflow with worker running"""
    print("🧪 Testing complete workflow execution...")
    
    # Enable logging
    logging.basicConfig(level=logging.INFO)
    
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
        
        print("🚀 Starting worker and workflow...")
        
        # Use unique workflow ID
        workflow_id = f"test-complete-workflow-{uuid.uuid4().hex[:8]}"
        
        async with worker:
            # Create workflow input
            input_data = ChefWorkflowInput(
                recipe="Chicken Parmesan",
                goal="Create a step-by-step cooking plan"
            )
            
            # Start workflow
            handle = await client.start_workflow(
                ChefWorkflow.run,
                input_data,
                id=workflow_id,
                task_queue="chef-task-queue"
            )
            
            print(f"📋 Workflow started with ID: {workflow_id}")
            
            # Wait for completion with timeout
            try:
                result = await asyncio.wait_for(handle.result(), timeout=30.0)
                print(f"✅ Workflow completed!")
                print(f"📄 Result: {result}")
                
                # Get final state
                final_state = await handle.query(ChefWorkflow.get_state)
                print(f"📊 Final state: {final_state.status}")
                print(f"🔧 Tools used: {final_state.used_tools}")
                print(f"📝 Steps completed: {len(final_state.completed_steps)}")
                
                return True
                
            except asyncio.TimeoutError:
                print("⏰ Workflow didn't complete within 30 seconds")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    success = asyncio.run(test_complete_workflow())
    print(f"\n{'🎉 SUCCESS!' if success else '❌ FAILED'}")