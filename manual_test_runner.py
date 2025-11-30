"""Manual test runner for ACP tests."""

import tempfile
import sys
from pathlib import Path

# Import modules
from acp.creator import AgentCreator
from acp.validator import ProposalValidator
from acp.registrar import AgentRegistrar

def test_creator():
    """Test AgentCreator."""
    print("Testing AgentCreator...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Use actual template
        template_dir = Path(__file__).parent / 'agents' / 'templates' / 'base_agent'
        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        metadata = creator.create_proposal(
            name='test-agent',
            description='Test agent',
            capabilities=['test', 'validation']
        )

        assert metadata['name'] == 'test-agent'
        assert 'proposal_id' in metadata
        print(f"  [OK] Created proposal: {metadata['proposal_id']}")

        # Test validator
        validator = ProposalValidator()
        result = validator.validate_proposal(metadata['path'])

        assert result['valid'] is True
        print(f"  [OK] Validation passed")

        # Test registrar
        registry_path = tmpdir_path / 'registry.json'
        registrar = AgentRegistrar(registry_path=str(registry_path))

        reg_result = registrar.register_agent(metadata['path'])

        assert reg_result['registered'] is True
        print(f"  [OK] Registration successful")

    print("[SUCCESS] All ACP components working!")

if __name__ == '__main__':
    try:
        test_creator()
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
