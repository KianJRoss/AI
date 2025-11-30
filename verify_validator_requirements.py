"""
Verification script to confirm ProposalValidator meets all requirements.
"""

from acp.creator import AgentCreator
from acp.validator import ProposalValidator
import tempfile
from pathlib import Path

def verify_requirements():
    """Verify ProposalValidator meets all specified requirements."""

    print("=" * 70)
    print("VERIFYING ProposalValidator REQUIREMENTS")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Setup
        template_dir = Path(__file__).parent / 'agents' / 'templates' / 'base_agent'
        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(
            template_dir=str(template_dir),
            proposals_dir=str(proposals_dir)
        )

        validator = ProposalValidator()

        # Create a valid proposal for testing
        metadata = creator.create_proposal(
            name='test-validator',
            description='Testing validator requirements',
            capabilities=['test', 'validation']
        )

        proposal_path = metadata['path']

        print("\n[REQUIREMENT 1] Ensure path exists")
        print("-" * 70)

        # Test with valid path
        result = validator.validate_proposal(proposal_path)
        assert result is not None, "Should return a result"
        print("  [OK] Returns result for existing path")

        # Test with non-existent path
        result = validator.validate_proposal('/nonexistent/path')
        assert result['valid'] is False, "Should be invalid for non-existent path"
        assert len(result['errors']) > 0, "Should have errors"
        assert 'does not exist' in result['errors'][0], "Should mention path doesn't exist"
        print("  [OK] Detects non-existent path")
        print(f"       Error: {result['errors'][0]}")

        print("\n[REQUIREMENT 2] Confirm agent.yaml exists")
        print("-" * 70)

        # Create proposal without agent.yaml
        bad_proposal = tmpdir_path / 'no_yaml'
        bad_proposal.mkdir()
        (bad_proposal / 'main.py').write_text("# main")
        (bad_proposal / 'tests').mkdir()

        result = validator.validate_proposal(str(bad_proposal))
        assert result['valid'] is False
        assert any('agent.yaml' in error for error in result['errors'])
        print("  [OK] Detects missing agent.yaml")
        print(f"       Error: {[e for e in result['errors'] if 'agent.yaml' in e][0]}")

        print("\n[REQUIREMENT 3] Confirm main.py exists")
        print("-" * 70)

        # Create proposal without main.py
        no_main = tmpdir_path / 'no_main'
        no_main.mkdir()
        (no_main / 'agent.yaml').write_text("name: test\ndescription: Test\ncapabilities: []\nproposal_id: test\ncreated_at: 2025-11-30T12:00:00+00:00")
        (no_main / 'tests').mkdir()

        result = validator.validate_proposal(str(no_main))
        assert result['valid'] is False
        assert any('main.py' in error for error in result['errors'])
        print("  [OK] Detects missing main.py")
        print(f"       Error: {[e for e in result['errors'] if 'main.py' in e][0]}")

        print("\n[REQUIREMENT 4] Confirm tests/ folder exists")
        print("-" * 70)

        # Create proposal without tests/
        no_tests = tmpdir_path / 'no_tests'
        no_tests.mkdir()
        (no_tests / 'agent.yaml').write_text("name: test\ndescription: Test\ncapabilities: []\nproposal_id: test\ncreated_at: 2025-11-30T12:00:00+00:00")
        (no_tests / 'main.py').write_text("# main")

        result = validator.validate_proposal(str(no_tests))
        assert result['valid'] is False
        assert any('tests' in error for error in result['errors'])
        print("  [OK] Detects missing tests/ directory")
        print(f"       Error: {[e for e in result['errors'] if 'tests' in e][0]}")

        # Also check for at least one test file (warning)
        empty_tests = tmpdir_path / 'empty_tests'
        empty_tests.mkdir()
        (empty_tests / 'agent.yaml').write_text("name: test\ndescription: Test\ncapabilities: []\nproposal_id: test\ncreated_at: 2025-11-30T12:00:00+00:00")
        (empty_tests / 'main.py').write_text("# main")
        (empty_tests / 'tests').mkdir()

        result = validator.validate_proposal(str(empty_tests))
        assert result['valid'] is True  # Structure valid
        assert any('No test files' in warning for warning in result['warnings'])
        print("  [OK] Warns when no test files in tests/")
        print(f"       Warning: {[w for w in result['warnings'] if 'test files' in w][0]}")

        print("\n[REQUIREMENT 5] Load agent.yaml and verify fields")
        print("-" * 70)

        required_fields = ['name', 'description', 'capabilities', 'proposal_id', 'created_at']

        for field in required_fields:
            # Create proposal missing this field
            missing_field = tmpdir_path / f'missing_{field}'
            missing_field.mkdir()

            # Build YAML without the current field
            yaml_content = []
            if field != 'name':
                yaml_content.append('name: test')
            if field != 'description':
                yaml_content.append('description: Test description')
            if field != 'capabilities':
                yaml_content.append('capabilities: []')
            if field != 'proposal_id':
                yaml_content.append('proposal_id: test-123')
            if field != 'created_at':
                yaml_content.append('created_at: 2025-11-30T12:00:00+00:00')

            (missing_field / 'agent.yaml').write_text('\n'.join(yaml_content))
            (missing_field / 'main.py').write_text("# main")
            (missing_field / 'tests').mkdir()

            result = validator.validate_proposal(str(missing_field))
            assert result['valid'] is False
            assert any(field in error for error in result['errors'])
            print(f"  [OK] Detects missing '{field}' field")

        # Verify capabilities must be a list
        bad_caps = tmpdir_path / 'bad_capabilities'
        bad_caps.mkdir()
        (bad_caps / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: "not a list"
proposal_id: test-123
created_at: 2025-11-30T12:00:00+00:00
""")
        (bad_caps / 'main.py').write_text("# main")
        (bad_caps / 'tests').mkdir()

        result = validator.validate_proposal(str(bad_caps))
        assert result['valid'] is False
        assert any('list' in error.lower() for error in result['errors'])
        print(f"  [OK] Validates capabilities is a list")
        print(f"       Error: {[e for e in result['errors'] if 'list' in e.lower()][0]}")

        print("\n[REQUIREMENT 6] Return structured result dict")
        print("-" * 70)

        # Test valid proposal
        result = validator.validate_proposal(proposal_path)

        # Check structure
        assert isinstance(result, dict), "Result must be a dict"
        assert 'valid' in result, "Result must have 'valid' key"
        assert 'errors' in result, "Result must have 'errors' key"
        assert 'warnings' in result, "Result must have 'warnings' key"

        assert isinstance(result['valid'], bool), "'valid' must be boolean"
        assert isinstance(result['errors'], list), "'errors' must be list"
        assert isinstance(result['warnings'], list), "'warnings' must be list"

        print("  [OK] Returns dict with 'valid' (bool)")
        print("  [OK] Returns dict with 'errors' (list)")
        print("  [OK] Returns dict with 'warnings' (list)")

        # Verify valid proposal has valid=True
        assert result['valid'] is True, "Valid proposal should have valid=True"
        assert len(result['errors']) == 0, "Valid proposal should have no errors"
        print("  [OK] Valid proposal returns valid=True")
        print("  [OK] Valid proposal returns empty errors list")

        # Show example result
        print("\nExample result structure:")
        print(f"  {{'valid': {result['valid']}, 'errors': {result['errors']}, 'warnings': {result['warnings'][:1]}...}}")

        print("\n" + "=" * 70)
        print("ALL REQUIREMENTS VERIFIED SUCCESSFULLY!")
        print("=" * 70)
        print("\nSummary:")
        print("  [OK] Requirement 1: Path existence validation")
        print("  [OK] Requirement 2: agent.yaml existence check")
        print("  [OK] Requirement 3: main.py existence check")
        print("  [OK] Requirement 4: tests/ folder existence check")
        print("  [OK] Requirement 5: YAML field validation")
        print("       - name")
        print("       - description")
        print("       - capabilities (list)")
        print("       - proposal_id")
        print("       - created_at")
        print("  [OK] Requirement 6: Structured result dict")
        print("       - valid: bool")
        print("       - errors: list")
        print("       - warnings: list")
        print("\n[SUCCESS] ProposalValidator fully compliant with all requirements!")

if __name__ == '__main__':
    verify_requirements()
