import asyncio
import logging
from temporalio.client import Client
from workflow import ChefWorkflow, ChefWorkflowInput


async def test_basic_workflow():
    """Test basic workflow execution without LLM integration"""
    print("🧪 Testing Stage 1: Basic workflow execution...")
    
    # Enable logging to see what's happening
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Connect to Temporal server
        client = await Client.connect("localhost:7233")
        
        # Create workflow input
        input_data = ChefWorkflowInput(
            recipe="Chicken Parmesan",
            goal="Create a step-by-step cooking plan"
        )
        
        # Start the workflow with unique ID
        import uuid
        workflow_id = f"test-chef-workflow-{uuid.uuid4().hex[:8]}"
        print(f"🚀 Starting workflow with ID: {workflow_id}")
        handle = await client.start_workflow(
            ChefWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue="chef-task-queue"
        )
        
        print(f"📋 Workflow started with ID: {handle.id}")
        
        # Poll workflow state a few times to see progress
        for i in range(3):
            await asyncio.sleep(1)
            try:
                state = await handle.query(ChefWorkflow.get_state)
                print(f"📊 State check {i+1}: {state.status}")
                if state.current_step:
                    print(f"   Current step: {state.current_step}")
                if state.plan:
                    print(f"   Plan steps: {len(state.plan)}")
            except Exception as e:
                print(f"   Query error: {e}")
        
        # Wait for completion with timeout
        print("⏳ Waiting for workflow completion...")
        print("⚠️  Note: Make sure worker.py is running in another terminal!")
        
        try:
            result = await asyncio.wait_for(handle.result(), timeout=30.0)
            print(f"✅ Workflow completed!")
            print(f"📄 Result: {result}")
            
            # Get final state
            final_state = await handle.query(ChefWorkflow.get_state)
            print(f"📊 Final state: {final_state.status}")
            print(f"🔧 Tools used: {final_state.used_tools}")
        except asyncio.TimeoutError:
            print("⏰ Workflow didn't complete within 30 seconds")
            print("💡 This is expected if no worker is running")
            print("🚀 Start worker.py in another terminal to see execution")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_basic_workflow())