"""
Basic tests for base agent template.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import Agent


def test_agent_initialization():
    """Test agent can be initialized."""
    agent = Agent({'name': 'test_agent'})
    assert agent.name == 'test_agent'


def test_agent_execution():
    """Test agent can execute basic task."""
    agent = Agent()

    task = {
        'type': 'test',
        'data': 'test data'
    }

    result = agent.execute(task)

    assert result['success'] is True
    assert 'result' in result


def test_task_validation():
    """Test task validation."""
    agent = Agent()

    # Valid task
    valid_task = {'type': 'test', 'data': 'data'}
    assert agent.validate_task(valid_task) is True

    # Invalid task - not a dict
    assert agent.validate_task("not a dict") is False

    # Invalid task - missing type
    assert agent.validate_task({'data': 'data'}) is False


def test_agent_default_config():
    """Test agent with no config."""
    agent = Agent()
    assert agent.config == {}
    assert agent.name == 'base_agent'
