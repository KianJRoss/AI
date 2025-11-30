"""
Base Agent - Template for new agent proposals.

This file should be customized for each agent's specific functionality.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Agent:
    """Base agent implementation."""

    def __init__(self, config: dict = None):
        """
        Initialize agent.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.name = self.config.get('name', 'base_agent')
        logger.info(f"Agent '{self.name}' initialized")

    def execute(self, task: dict) -> dict:
        """
        Execute a task.

        Args:
            task: Task specification dictionary

        Returns:
            Result dictionary with status and output
        """
        logger.info(f"Executing task: {task.get('type', 'unknown')}")

        # Template implementation - override in specific agents
        return {
            'success': True,
            'result': 'Template agent executed',
            'agent': self.name
        }

    def validate_task(self, task: dict) -> bool:
        """
        Validate task specification.

        Args:
            task: Task specification

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(task, dict):
            return False

        if 'type' not in task:
            return False

        return True


def main():
    """Entry point for agent execution."""
    agent = Agent({'name': 'base_agent'})

    sample_task = {
        'type': 'test',
        'data': 'sample data'
    }

    if agent.validate_task(sample_task):
        result = agent.execute(sample_task)
        logger.info(f"Result: {result}")
    else:
        logger.error("Invalid task specification")


if __name__ == '__main__':
    main()
