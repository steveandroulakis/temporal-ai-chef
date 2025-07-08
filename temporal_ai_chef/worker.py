import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from .workflow import ChefWorkflow
from .activities import ChefActivities


async def main():
    # Set up logging to see activity execution
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Run the worker
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
            chef_activities.get_ingredients_for_step,
            chef_activities.use_tool
        ],
        # Activities need an executor for synchronous operations
        activity_executor=ThreadPoolExecutor(max_workers=5)
    )
    
    print("🍳 Chef Worker started! Waiting for workflows...")
    print("Task queue: chef-task-queue")
    print("Press Ctrl+C to stop")
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        print("\n👋 Chef Worker shutting down...")


def main_sync():
    """Synchronous entry point for console script"""
    asyncio.run(main())

if __name__ == "__main__":
    main_sync()