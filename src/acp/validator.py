"""
Proposal Validator - Checks agent proposal structure and metadata.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class ProposalValidator:
    """
    Validates agent proposal structure and metadata.
    """

    REQUIRED_FILES = [
        'agent.yaml',
        'main.py',
        'tests'
    ]

    REQUIRED_YAML_FIELDS = [
        'name',
        'description',
        'capabilities',
        'proposal_id',
        'created_at'
    ]

    def __init__(self):
        """Initialize ProposalValidator."""
        logger.info("ProposalValidator initialized")

    def validate_proposal(self, path: str) -> Dict:
        """
        Validate an agent proposal.

        Args:
            path: Path to proposal directory

        Returns:
            Dictionary with:
            - valid: Boolean indicating if proposal is valid
            - errors: List of error messages
            - warnings: List of warning messages
        """
        logger.info(f"Validating proposal: {path}")

        proposal_path = Path(path)
        errors = []
        warnings = []

        # Check if path exists
        if not proposal_path.exists():
            errors.append(f"Proposal path does not exist: {path}")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings
            }

        if not proposal_path.is_dir():
            errors.append(f"Proposal path is not a directory: {path}")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings
            }

        # Check required files
        for required_file in self.REQUIRED_FILES:
            file_path = proposal_path / required_file

            if not file_path.exists():
                errors.append(f"Missing required file/directory: {required_file}")

        # Validate agent.yaml if it exists
        agent_yaml_path = proposal_path / 'agent.yaml'

        if agent_yaml_path.exists():
            try:
                with open(agent_yaml_path, 'r') as f:
                    agent_config = yaml.safe_load(f)

                # Check required fields
                for field in self.REQUIRED_YAML_FIELDS:
                    if field not in agent_config:
                        errors.append(f"Missing required YAML field: {field}")
                    elif agent_config[field] is None or agent_config[field] == '':
                        errors.append(f"Empty required YAML field: {field}")

                # Validate capabilities is a list
                if 'capabilities' in agent_config:
                    if not isinstance(agent_config['capabilities'], list):
                        errors.append("Field 'capabilities' must be a list")

                # Warnings for optional fields
                if 'version' not in agent_config:
                    warnings.append("Optional field 'version' not specified")

                if 'entrypoint' not in agent_config:
                    warnings.append("Optional field 'entrypoint' not specified, defaulting to main.py")

                if 'tests' not in agent_config:
                    warnings.append("Optional field 'tests' not specified")

            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML syntax in agent.yaml: {e}")

            except Exception as e:
                errors.append(f"Error reading agent.yaml: {e}")

        # Check main.py is not empty
        main_py_path = proposal_path / 'main.py'

        if main_py_path.exists():
            try:
                content = main_py_path.read_text()

                if len(content.strip()) == 0:
                    warnings.append("main.py is empty")

            except Exception as e:
                warnings.append(f"Could not read main.py: {e}")

        # Check tests directory
        tests_dir = proposal_path / 'tests'

        if tests_dir.exists():
            if not tests_dir.is_dir():
                errors.append("'tests' exists but is not a directory")
            else:
                # Check if tests directory has any test files
                test_files = list(tests_dir.glob('test_*.py'))

                if len(test_files) == 0:
                    warnings.append("No test files found in tests/ directory")

        # Determine validity
        valid = len(errors) == 0

        if valid:
            logger.info(f"Proposal validation passed: {path}")
        else:
            logger.warning(f"Proposal validation failed: {path} - {len(errors)} errors")

        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings
        }

    def validate_yaml_only(self, yaml_path: str) -> Dict:
        """
        Validate just the agent.yaml file.

        Args:
            yaml_path: Path to agent.yaml file

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        yaml_path_obj = Path(yaml_path)

        if not yaml_path_obj.exists():
            errors.append(f"YAML file does not exist: {yaml_path}")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings
            }

        try:
            with open(yaml_path_obj, 'r') as f:
                agent_config = yaml.safe_load(f)

            # Check required fields
            for field in self.REQUIRED_YAML_FIELDS:
                if field not in agent_config:
                    errors.append(f"Missing required YAML field: {field}")

            # Validate capabilities is a list
            if 'capabilities' in agent_config and not isinstance(agent_config['capabilities'], list):
                errors.append("Field 'capabilities' must be a list")

        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {e}")

        except Exception as e:
            errors.append(f"Error reading YAML: {e}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


if __name__ == '__main__':
    # Test validation
    import sys

    if len(sys.argv) > 1:
        proposal_path = sys.argv[1]
    else:
        print("Usage: python validator.py <proposal_path>")
        sys.exit(1)

    validator = ProposalValidator()
    result = validator.validate_proposal(proposal_path)

    print(f"Valid: {result['valid']}")
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
