"""
Unit tests for AgentCreator.
"""

import tempfile
import yaml
from pathlib import Path

from acp.creator import AgentCreator


def test_create_proposal_basic():
    """Test basic proposal creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create template
        template_dir = tmpdir_path / 'template'
        template_dir.mkdir()

        (template_dir / 'agent.yaml').write_text("""
name: template
description: Template
capabilities: []
""")

        (template_dir / 'main.py').write_text("# Template main.py")

        tests_dir = template_dir / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

        # Create proposals directory
        proposals_dir = tmpdir_path / 'proposals'

        # Create agent
        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        metadata = creator.create_proposal(
            name='test-agent',
            description='Test agent',
            capabilities=['test', 'validation']
        )

        # Assertions
        assert metadata['name'] == 'test-agent'
        assert metadata['capabilities'] == ['test', 'validation']
        assert 'proposal_id' in metadata
        assert 'created_at' in metadata
        assert 'path' in metadata

        # Check proposal directory exists
        proposal_path = Path(metadata['path'])
        assert proposal_path.exists()
        assert proposal_path.is_dir()

        # Check files
        assert (proposal_path / 'agent.yaml').exists()
        assert (proposal_path / 'main.py').exists()
        assert (proposal_path / 'tests').exists()


def test_proposal_yaml_fields():
    """Test that YAML fields are correctly populated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create template
        template_dir = tmpdir_path / 'template'
        template_dir.mkdir()

        (template_dir / 'agent.yaml').write_text("""
name: template
description: Template
capabilities: []
""")

        (template_dir / 'main.py').write_text("# Template")

        tests_dir = template_dir / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        metadata = creator.create_proposal(
            name='graph-analyzer',
            description='Analyzes graph structures',
            capabilities=['graph', 'analysis']
        )

        # Load YAML and check fields
        proposal_path = Path(metadata['path'])
        agent_yaml_path = proposal_path / 'agent.yaml'

        with open(agent_yaml_path, 'r') as f:
            agent_config = yaml.safe_load(f)

        assert agent_config['name'] == 'graph-analyzer'
        assert agent_config['description'] == 'Analyzes graph structures'
        assert agent_config['capabilities'] == ['graph', 'analysis']
        assert agent_config['proposal_id'] == metadata['proposal_id']
        assert agent_config['created_at'] == metadata['created_at']


def test_unique_proposal_ids():
    """Test that proposal IDs are unique."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create template
        template_dir = tmpdir_path / 'template'
        template_dir.mkdir()

        (template_dir / 'agent.yaml').write_text("name: template\ndescription: Template\ncapabilities: []")
        (template_dir / 'main.py').write_text("# Template")

        tests_dir = template_dir / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        # Create multiple proposals
        proposal_ids = set()

        for i in range(5):
            metadata = creator.create_proposal(
                name=f'agent-{i}',
                description=f'Agent {i}',
                capabilities=['test']
            )

            proposal_ids.add(metadata['proposal_id'])

        # All IDs should be unique
        assert len(proposal_ids) == 5


def test_template_not_found():
    """Test error handling when template doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Non-existent template
        template_dir = tmpdir_path / 'nonexistent'
        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        try:
            creator.create_proposal(
                name='test',
                description='Test',
                capabilities=[]
            )
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass


def test_proposal_cleanup_on_failure():
    """Test that failed proposals are cleaned up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create template WITHOUT agent.yaml (will cause failure)
        template_dir = tmpdir_path / 'template'
        template_dir.mkdir()

        (template_dir / 'main.py').write_text("# Template")

        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        try:
            creator.create_proposal(
                name='test',
                description='Test',
                capabilities=[]
            )
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass

        # Check that no proposals were left behind
        if proposals_dir.exists():
            proposals = list(proposals_dir.iterdir())
            assert len(proposals) == 0


def test_proposal_id_format():
    """Test that proposal ID has correct format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create template
        template_dir = tmpdir_path / 'template'
        template_dir.mkdir()

        (template_dir / 'agent.yaml').write_text("name: template\ndescription: Template\ncapabilities: []")
        (template_dir / 'main.py').write_text("# Template")

        tests_dir = template_dir / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        metadata = creator.create_proposal(
            name='test',
            description='Test',
            capabilities=[]
        )

        proposal_id = metadata['proposal_id']

        # Check format: proposal-<timestamp>-<random>
        assert proposal_id.startswith('proposal-')

        parts = proposal_id.split('-')
        assert len(parts) == 3

        # Timestamp should be 14 digits
        assert len(parts[1]) == 14
        assert parts[1].isdigit()

        # Random suffix should be 4 chars
        assert len(parts[2]) == 4
