"""
Unit tests for AgentRegistrar.
"""

import tempfile
import json
from pathlib import Path

from acp.registrar import AgentRegistrar


def create_test_proposal(base_dir: Path, name: str = 'test_agent') -> Path:
    """Helper to create a test proposal."""
    proposal_dir = base_dir / f'proposal-{name}'
    proposal_dir.mkdir()

    (proposal_dir / 'agent.yaml').write_text(f"""
name: {name}
description: Test agent for {name}
capabilities:
  - test
  - validation
proposal_id: proposal-{name}-1234
created_at: 2025-11-30T12:00:00+00:00
version: 1.0.0
""")

    (proposal_dir / 'main.py').write_text("# Main code")

    tests_dir = proposal_dir / 'tests'
    tests_dir.mkdir()
    (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

    return proposal_dir


def test_register_agent_basic():
    """Test basic agent registration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create proposal
        proposal_dir = create_test_proposal(tmpdir_path)

        # Create registry
        registry_path = tmpdir_path / 'registry.json'

        registrar = AgentRegistrar(registry_path=str(registry_path))

        result = registrar.register_agent(str(proposal_dir))

        assert result['registered'] is True
        assert result['error'] is None
        assert result['entry'] is not None

        # Check entry fields
        entry = result['entry']
        assert entry['name'] == 'test_agent'
        assert entry['id'] == 'proposal-test_agent-1234'
        assert entry['description'] == 'Test agent for test_agent'
        assert entry['capabilities'] == ['test', 'validation']
        assert 'added_at' in entry
        assert 'path' in entry

        # Check registry file exists
        assert registry_path.exists()


def test_register_multiple_agents():
    """Test registering multiple agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        # Register 3 agents
        for i in range(3):
            proposal_dir = create_test_proposal(tmpdir_path, name=f'agent_{i}')
            result = registrar.register_agent(str(proposal_dir))

            assert result['registered'] is True

        # Check registry contains all 3
        registry = registrar.get_registry()
        assert len(registry) == 3

        # Check names
        names = [entry['name'] for entry in registry]
        assert 'agent_0' in names
        assert 'agent_1' in names
        assert 'agent_2' in names


def test_register_duplicate_creates_two_entries():
    """Test that registering same agent twice creates two entries (not merge)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = create_test_proposal(tmpdir_path)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        # Register same agent twice
        result1 = registrar.register_agent(str(proposal_dir))
        result2 = registrar.register_agent(str(proposal_dir))

        assert result1['registered'] is True
        assert result2['registered'] is True

        # Check registry has 2 entries (not merged)
        registry = registrar.get_registry()
        assert len(registry) == 2

        # Both should have same ID
        assert registry[0]['id'] == registry[1]['id']


def test_register_nonexistent_proposal():
    """Test error handling for nonexistent proposal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        result = registrar.register_agent('/nonexistent/proposal')

        assert result['registered'] is False
        assert result['error'] is not None
        assert 'does not exist' in result['error']


def test_register_missing_yaml():
    """Test error handling when agent.yaml is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create proposal without agent.yaml
        proposal_dir = tmpdir_path / 'proposal'
        proposal_dir.mkdir()

        (proposal_dir / 'main.py').write_text("# Main")

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        result = registrar.register_agent(str(proposal_dir))

        assert result['registered'] is False
        assert result['error'] is not None


def test_register_with_preloaded_yaml():
    """Test registration with pre-loaded YAML dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create proposal
        proposal_dir = create_test_proposal(tmpdir_path)

        # Pre-load YAML
        proposal_yaml = {
            'name': 'custom-agent',
            'proposal_id': 'proposal-custom-5678',
            'description': 'Custom description',
            'capabilities': ['custom']
        }

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        result = registrar.register_agent(str(proposal_dir), proposal_yaml=proposal_yaml)

        assert result['registered'] is True

        # Check it used the pre-loaded YAML
        entry = result['entry']
        assert entry['name'] == 'custom-agent'
        assert entry['id'] == 'proposal-custom-5678'


def test_get_registry():
    """Test retrieving full registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        # Register agents
        for i in range(3):
            proposal_dir = create_test_proposal(tmpdir_path, name=f'agent_{i}')
            registrar.register_agent(str(proposal_dir))

        registry = registrar.get_registry()

        assert len(registry) == 3
        assert isinstance(registry, list)


def test_get_agent_by_id():
    """Test retrieving agent by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        # Register agent
        proposal_dir = create_test_proposal(tmpdir_path, name='my_agent')
        result = registrar.register_agent(str(proposal_dir))

        agent_id = result['entry']['id']

        # Retrieve by ID
        entry = registrar.get_agent_by_id(agent_id)

        assert entry is not None
        assert entry['id'] == agent_id
        assert entry['name'] == 'my_agent'


def test_get_agent_by_id_not_found():
    """Test retrieving non-existent agent by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        entry = registrar.get_agent_by_id('nonexistent-id')

        assert entry is None


def test_get_agents_by_capability():
    """Test retrieving agents by capability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        # Register agents with different capabilities
        proposal_dir1 = tmpdir_path / 'proposal1'
        proposal_dir1.mkdir()
        (proposal_dir1 / 'agent.yaml').write_text("""
name: agent1
description: Agent 1
capabilities: [graph, analysis]
proposal_id: proposal-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (proposal_dir1 / 'main.py').write_text("# Main")
        tests_dir1 = proposal_dir1 / 'tests'
        tests_dir1.mkdir()

        proposal_dir2 = tmpdir_path / 'proposal2'
        proposal_dir2.mkdir()
        (proposal_dir2 / 'agent.yaml').write_text("""
name: agent2
description: Agent 2
capabilities: [data, analysis]
proposal_id: proposal-2
created_at: 2025-11-30T12:00:00+00:00
""")
        (proposal_dir2 / 'main.py').write_text("# Main")
        tests_dir2 = proposal_dir2 / 'tests'
        tests_dir2.mkdir()

        registrar.register_agent(str(proposal_dir1))
        registrar.register_agent(str(proposal_dir2))

        # Get agents with 'analysis' capability
        matching = registrar.get_agents_by_capability('analysis')

        assert len(matching) == 2

        # Get agents with 'graph' capability
        matching = registrar.get_agents_by_capability('graph')

        assert len(matching) == 1
        assert matching[0]['name'] == 'agent1'


def test_empty_registry():
    """Test handling empty registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        registry = registrar.get_registry()

        assert registry == []


def test_registry_persistence():
    """Test that registry persists across instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        registry_path = tmpdir_path / 'registry.json'

        # First registrar instance
        registrar1 = AgentRegistrar(registry_path=str(registry_path))

        proposal_dir = create_test_proposal(tmpdir_path)
        registrar1.register_agent(str(proposal_dir))

        # Second registrar instance
        registrar2 = AgentRegistrar(registry_path=str(registry_path))

        registry = registrar2.get_registry()

        assert len(registry) == 1
        assert registry[0]['name'] == 'test_agent'
