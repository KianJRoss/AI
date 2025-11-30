"""
Unit tests for ProposalValidator.
"""

import tempfile
from pathlib import Path

from acp.validator import ProposalValidator


def create_valid_proposal(base_dir: Path) -> Path:
    """Helper to create a valid proposal."""
    proposal_dir = base_dir / 'test_proposal'
    proposal_dir.mkdir()

    # Create agent.yaml
    (proposal_dir / 'agent.yaml').write_text("""
name: test_agent
description: Test agent
capabilities:
  - test
  - validation
proposal_id: proposal-test-1234
created_at: 2025-11-30T12:00:00+00:00
version: 1.0.0
entrypoint: main.py
""")

    # Create main.py
    (proposal_dir / 'main.py').write_text("# Main code")

    # Create tests directory
    tests_dir = proposal_dir / 'tests'
    tests_dir.mkdir()
    (tests_dir / 'test_basic.py').write_text("def test_pass(): assert True")

    return proposal_dir


def test_validate_valid_proposal():
    """Test validating a valid proposal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = create_valid_proposal(tmpdir_path)

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is True
        assert len(result['errors']) == 0


def test_validate_missing_path():
    """Test validation with non-existent path."""
    validator = ProposalValidator()

    result = validator.validate_proposal('/nonexistent/path')

    assert result['valid'] is False
    assert len(result['errors']) > 0
    assert 'does not exist' in result['errors'][0]


def test_validate_missing_agent_yaml():
    """Test validation with missing agent.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Create main.py and tests, but NOT agent.yaml
        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('agent.yaml' in error for error in result['errors'])


def test_validate_missing_main_py():
    """Test validation with missing main.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Create agent.yaml and tests, but NOT main.py
        (proposal_dir / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: []
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('main.py' in error for error in result['errors'])


def test_validate_missing_tests_directory():
    """Test validation with missing tests directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        (proposal_dir / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: []
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        (proposal_dir / 'main.py').write_text("# Main")

        # No tests directory

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('tests' in error for error in result['errors'])


def test_validate_missing_yaml_fields():
    """Test validation with missing required YAML fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Missing 'description' and 'proposal_id'
        (proposal_dir / 'agent.yaml').write_text("""
name: test
capabilities: []
created_at: 2025-11-30T12:00:00+00:00
""")

        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('description' in error for error in result['errors'])
        assert any('proposal_id' in error for error in result['errors'])


def test_validate_empty_yaml_fields():
    """Test validation with empty required YAML fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Empty name and description
        (proposal_dir / 'agent.yaml').write_text("""
name: ""
description: ""
capabilities: []
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('Empty' in error and 'name' in error for error in result['errors'])


def test_validate_capabilities_not_list():
    """Test validation when capabilities is not a list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        (proposal_dir / 'agent.yaml').write_text("""
name: test
description: Test agent
capabilities: "not a list"
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('capabilities' in error and 'list' in error for error in result['errors'])


def test_validate_warnings():
    """Test validation warnings for missing optional fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Valid but without optional fields
        (proposal_dir / 'agent.yaml').write_text("""
name: test
description: Test agent
capabilities: []
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is True
        assert len(result['warnings']) > 0


def test_validate_empty_tests_directory():
    """Test warning when tests directory has no test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = create_valid_proposal(tmpdir_path)

        # Remove test files
        for test_file in (proposal_dir / 'tests').glob('*.py'):
            test_file.unlink()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is True
        assert any('No test files' in warning for warning in result['warnings'])


def test_validate_invalid_yaml_syntax():
    """Test validation with invalid YAML syntax."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        proposal_dir = tmpdir_path / 'test_proposal'
        proposal_dir.mkdir()

        # Invalid YAML
        (proposal_dir / 'agent.yaml').write_text("""
name: test
  invalid indentation:
description: Test
""")

        (proposal_dir / 'main.py').write_text("# Main")

        tests_dir = proposal_dir / 'tests'
        tests_dir.mkdir()

        validator = ProposalValidator()
        result = validator.validate_proposal(str(proposal_dir))

        assert result['valid'] is False
        assert any('YAML' in error for error in result['errors'])


def test_validate_yaml_only():
    """Test validating just the YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        yaml_path = tmpdir_path / 'agent.yaml'
        yaml_path.write_text("""
name: test
description: Test agent
capabilities: [test]
proposal_id: test-1234
created_at: 2025-11-30T12:00:00+00:00
""")

        validator = ProposalValidator()
        result = validator.validate_yaml_only(str(yaml_path))

        assert result['valid'] is True
        assert len(result['errors']) == 0
