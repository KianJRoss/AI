"""
Complete test suite demonstrating ProposalValidator functionality.
Shows all validation scenarios with expected outcomes.
"""

from acp.creator import AgentCreator
from acp.validator import ProposalValidator
import tempfile
from pathlib import Path

def run_all_scenarios():
    """Run all validation scenarios."""

    print("=" * 70)
    print("COMPLETE ProposalValidator TEST SUITE")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        template_dir = Path(__file__).parent / 'agents' / 'templates' / 'base_agent'
        proposals_dir = tmpdir_path / 'proposals'

        creator = AgentCreator(template_dir=str(template_dir), proposals_dir=str(proposals_dir))
        validator = ProposalValidator()

        scenarios = []

        # SCENARIO 1: Perfect proposal
        print("\n[SCENARIO 1] Valid proposal with all requirements")
        print("-" * 70)
        metadata = creator.create_proposal(
            name='perfect-agent',
            description='A perfectly valid agent proposal',
            capabilities=['analysis', 'processing']
        )
        result = validator.validate_proposal(metadata['path'])
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        print(f"Warnings: {result['warnings']}")
        scenarios.append(("Valid proposal", result['valid'], True))

        # SCENARIO 2: Non-existent path
        print("\n[SCENARIO 2] Non-existent proposal path")
        print("-" * 70)
        result = validator.validate_proposal('/this/path/does/not/exist')
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Non-existent path", result['valid'], False))

        # SCENARIO 3: Missing agent.yaml
        print("\n[SCENARIO 3] Missing agent.yaml file")
        print("-" * 70)
        no_yaml = tmpdir_path / 'scenario3'
        no_yaml.mkdir()
        (no_yaml / 'main.py').write_text("# code")
        (no_yaml / 'tests').mkdir()
        (no_yaml / 'tests' / 'test_basic.py').write_text("def test(): pass")

        result = validator.validate_proposal(str(no_yaml))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing agent.yaml", result['valid'], False))

        # SCENARIO 4: Missing main.py
        print("\n[SCENARIO 4] Missing main.py file")
        print("-" * 70)
        no_main = tmpdir_path / 'scenario4'
        no_main.mkdir()
        (no_main / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (no_main / 'tests').mkdir()

        result = validator.validate_proposal(str(no_main))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing main.py", result['valid'], False))

        # SCENARIO 5: Missing tests/ directory
        print("\n[SCENARIO 5] Missing tests/ directory")
        print("-" * 70)
        no_tests = tmpdir_path / 'scenario5'
        no_tests.mkdir()
        (no_tests / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (no_tests / 'main.py').write_text("# code")

        result = validator.validate_proposal(str(no_tests))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing tests/", result['valid'], False))

        # SCENARIO 6: Missing 'name' field
        print("\n[SCENARIO 6] Missing 'name' in agent.yaml")
        print("-" * 70)
        no_name = tmpdir_path / 'scenario6'
        no_name.mkdir()
        (no_name / 'agent.yaml').write_text("""
description: Test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (no_name / 'main.py').write_text("# code")
        (no_name / 'tests').mkdir()

        result = validator.validate_proposal(str(no_name))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing name field", result['valid'], False))

        # SCENARIO 7: Missing 'description' field
        print("\n[SCENARIO 7] Missing 'description' in agent.yaml")
        print("-" * 70)
        no_desc = tmpdir_path / 'scenario7'
        no_desc.mkdir()
        (no_desc / 'agent.yaml').write_text("""
name: test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (no_desc / 'main.py').write_text("# code")
        (no_desc / 'tests').mkdir()

        result = validator.validate_proposal(str(no_desc))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing description", result['valid'], False))

        # SCENARIO 8: Missing 'capabilities' field
        print("\n[SCENARIO 8] Missing 'capabilities' in agent.yaml")
        print("-" * 70)
        no_caps = tmpdir_path / 'scenario8'
        no_caps.mkdir()
        (no_caps / 'agent.yaml').write_text("""
name: test
description: Test
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (no_caps / 'main.py').write_text("# code")
        (no_caps / 'tests').mkdir()

        result = validator.validate_proposal(str(no_caps))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Missing capabilities", result['valid'], False))

        # SCENARIO 9: capabilities not a list
        print("\n[SCENARIO 9] capabilities field is not a list")
        print("-" * 70)
        bad_caps = tmpdir_path / 'scenario9'
        bad_caps.mkdir()
        (bad_caps / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: "not a list"
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (bad_caps / 'main.py').write_text("# code")
        (bad_caps / 'tests').mkdir()

        result = validator.validate_proposal(str(bad_caps))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Capabilities not list", result['valid'], False))

        # SCENARIO 10: Empty required field
        print("\n[SCENARIO 10] Empty 'name' field")
        print("-" * 70)
        empty_name = tmpdir_path / 'scenario10'
        empty_name.mkdir()
        (empty_name / 'agent.yaml').write_text("""
name: ""
description: Test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (empty_name / 'main.py').write_text("# code")
        (empty_name / 'tests').mkdir()

        result = validator.validate_proposal(str(empty_name))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        scenarios.append(("Empty name field", result['valid'], False))

        # SCENARIO 11: Invalid YAML syntax
        print("\n[SCENARIO 11] Invalid YAML syntax")
        print("-" * 70)
        bad_yaml = tmpdir_path / 'scenario11'
        bad_yaml.mkdir()
        (bad_yaml / 'agent.yaml').write_text("""
name: test
  invalid: indentation
description: Test
""")
        (bad_yaml / 'main.py').write_text("# code")
        (bad_yaml / 'tests').mkdir()

        result = validator.validate_proposal(str(bad_yaml))
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors'][:1]}...")  # Show first error
        scenarios.append(("Invalid YAML syntax", result['valid'], False))

        # SCENARIO 12: No test files in tests/ (warning)
        print("\n[SCENARIO 12] No test files in tests/ directory")
        print("-" * 70)
        empty_tests = tmpdir_path / 'scenario12'
        empty_tests.mkdir()
        (empty_tests / 'agent.yaml').write_text("""
name: test
description: Test
capabilities: []
proposal_id: test-1
created_at: 2025-11-30T12:00:00+00:00
""")
        (empty_tests / 'main.py').write_text("# code")
        (empty_tests / 'tests').mkdir()

        result = validator.validate_proposal(str(empty_tests))
        print(f"Valid: {result['valid']}")
        print(f"Warnings: {result['warnings']}")
        scenarios.append(("Empty tests/", result['valid'], True))

        # Results summary
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)

        passed = 0
        failed = 0

        for scenario, actual, expected in scenarios:
            status = "PASS" if actual == expected else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {scenario}: valid={actual} (expected={expected})")

        print("\n" + "-" * 70)
        print(f"Total: {len(scenarios)} scenarios")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

        if failed == 0:
            print("\n[SUCCESS] All scenarios passed!")
        else:
            print(f"\n[FAILURE] {failed} scenario(s) failed!")

        return failed == 0

if __name__ == '__main__':
    import sys
    success = run_all_scenarios()
    sys.exit(0 if success else 1)
