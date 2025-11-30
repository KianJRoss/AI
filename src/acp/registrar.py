"""
Agent Registrar - Adds approved agents to registry.
"""

import json
import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class AgentRegistrar:
    """
    Manages agent registration in registry.json.
    """

    def __init__(self, registry_path: str = None):
        """
        Initialize AgentRegistrar.

        Args:
            registry_path: Path to registry.json file
        """
        if registry_path is None:
            # Default to agents/registry.json
            self.registry_path = Path(__file__).parent.parent.parent / 'agents' / 'registry.json'
        else:
            self.registry_path = Path(registry_path)

        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"AgentRegistrar initialized: registry={self.registry_path}")

    def _load_registry(self) -> list:
        """
        Load registry from file.

        Returns:
            List of registered agents
        """
        if not self.registry_path.exists():
            logger.debug("Registry file does not exist, returning empty list")
            return []

        try:
            with open(self.registry_path, 'r') as f:
                registry = json.load(f)

            if not isinstance(registry, list):
                logger.warning("Registry is not a list, returning empty list")
                return []

            return registry

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in registry file: {e}")
            return []

        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return []

    def _save_registry(self, registry: list) -> bool:
        """
        Save registry to file.

        Args:
            registry: List of registered agents

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(registry, f, indent=2, default=str)

            logger.debug(f"Registry saved: {len(registry)} entries")
            return True

        except Exception as e:
            logger.error(f"Error saving registry: {e}")
            return False

    def _load_proposal_yaml(self, proposal_path: str) -> Optional[dict]:
        """
        Load agent.yaml from proposal.

        Args:
            proposal_path: Path to proposal directory

        Returns:
            Parsed YAML dictionary or None if error
        """
        proposal_path_obj = Path(proposal_path)
        agent_yaml_path = proposal_path_obj / 'agent.yaml'

        if not agent_yaml_path.exists():
            logger.error(f"agent.yaml not found in proposal: {proposal_path}")
            return None

        try:
            with open(agent_yaml_path, 'r') as f:
                return yaml.safe_load(f)

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {agent_yaml_path}: {e}")
            return None

        except Exception as e:
            logger.error(f"Error reading {agent_yaml_path}: {e}")
            return None

    def register_agent(self, proposal_path: str, proposal_yaml: dict = None) -> Dict:
        """
        Register an approved agent proposal.

        Args:
            proposal_path: Path to proposal directory
            proposal_yaml: Optional pre-loaded YAML dict (if None, loads from proposal)

        Returns:
            Dictionary with:
            - registered: True if registered, False otherwise
            - entry: Registry entry dict (if registered)
            - error: Error message (if not registered)
        """
        logger.info(f"Registering agent from proposal: {proposal_path}")

        proposal_path_obj = Path(proposal_path)

        # Validate proposal path exists
        if not proposal_path_obj.exists():
            error_msg = f"Proposal path does not exist: {proposal_path}"
            logger.error(error_msg)
            return {
                'registered': False,
                'entry': None,
                'error': error_msg
            }

        # Load proposal YAML if not provided
        if proposal_yaml is None:
            proposal_yaml = self._load_proposal_yaml(proposal_path)

            if proposal_yaml is None:
                error_msg = "Failed to load agent.yaml from proposal"
                return {
                    'registered': False,
                    'entry': None,
                    'error': error_msg
                }

        # Validate required fields
        required_fields = ['name', 'proposal_id', 'description', 'capabilities']

        for field in required_fields:
            if field not in proposal_yaml:
                error_msg = f"Missing required field in proposal YAML: {field}"
                logger.error(error_msg)
                return {
                    'registered': False,
                    'entry': None,
                    'error': error_msg
                }

        # Create registry entry
        added_at = datetime.now(timezone.utc).isoformat()

        entry = {
            'name': proposal_yaml['name'],
            'id': proposal_yaml['proposal_id'],
            'description': proposal_yaml['description'],
            'capabilities': proposal_yaml['capabilities'],
            'added_at': added_at,
            'path': str(proposal_path_obj.resolve())
        }

        # Load current registry
        registry = self._load_registry()

        # Check if already registered (by ID)
        for existing_entry in registry:
            if existing_entry.get('id') == entry['id']:
                logger.warning(f"Agent with ID '{entry['id']}' already registered")
                # Allow duplicate registrations (as per spec: "two registrations should create two entries")
                # Note: This creates duplicates, not merge

        # Append new entry
        registry.append(entry)

        # Save registry
        if not self._save_registry(registry):
            error_msg = "Failed to save registry"
            return {
                'registered': False,
                'entry': None,
                'error': error_msg
            }

        logger.info(f"Agent registered successfully: {entry['name']} (ID: {entry['id']})")

        return {
            'registered': True,
            'entry': entry,
            'error': None
        }

    def get_registry(self) -> list:
        """
        Get all registered agents.

        Returns:
            List of registered agent entries
        """
        return self._load_registry()

    def get_agent_by_id(self, agent_id: str) -> Optional[dict]:
        """
        Get agent entry by ID.

        Args:
            agent_id: Agent/proposal ID

        Returns:
            Agent entry dict or None if not found
        """
        registry = self._load_registry()

        for entry in registry:
            if entry.get('id') == agent_id:
                return entry

        return None

    def get_agents_by_capability(self, capability: str) -> list:
        """
        Get all agents with a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching agent entries
        """
        registry = self._load_registry()
        matching = []

        for entry in registry:
            capabilities = entry.get('capabilities', [])

            if capability in capabilities:
                matching.append(entry)

        return matching


if __name__ == '__main__':
    # Test registration
    import sys

    if len(sys.argv) > 1:
        proposal_path = sys.argv[1]
    else:
        print("Usage: python registrar.py <proposal_path>")
        sys.exit(1)

    registrar = AgentRegistrar()
    result = registrar.register_agent(proposal_path)

    print(f"Registered: {result['registered']}")

    if result['registered']:
        print(f"Entry: {result['entry']}")
    else:
        print(f"Error: {result['error']}")
