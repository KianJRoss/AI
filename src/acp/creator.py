"""
Agent Creator - Generates agent proposal folders from templates.
"""

import logging
import shutil
import time
import random
import string
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class AgentCreator:
    """
    Creates agent proposals from templates.
    """

    def __init__(self, template_dir: str = None, proposals_dir: str = None):
        """
        Initialize AgentCreator.

        Args:
            template_dir: Path to templates directory
            proposals_dir: Path to proposals directory
        """
        if template_dir is None:
            # Default to agents/templates/base_agent
            self.template_dir = Path(__file__).parent.parent.parent / 'agents' / 'templates' / 'base_agent'
        else:
            self.template_dir = Path(template_dir)

        if proposals_dir is None:
            # Default to proposals/
            self.proposals_dir = Path(__file__).parent.parent.parent / 'proposals'
        else:
            self.proposals_dir = Path(proposals_dir)

        # Ensure proposals directory exists
        self.proposals_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AgentCreator initialized: template={self.template_dir}, proposals={self.proposals_dir}")

    def _generate_proposal_id(self) -> str:
        """
        Generate unique proposal ID.

        Returns:
            Proposal ID in format "proposal-<timestamp>-<random>"
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))

        proposal_id = f"proposal-{timestamp}-{random_suffix}"

        return proposal_id

    def _ensure_unique_proposal_path(self, max_retries: int = 10) -> tuple[str, Path]:
        """
        Generate unique proposal path with retries.

        Args:
            max_retries: Maximum number of retries

        Returns:
            Tuple of (proposal_id, proposal_path)

        Raises:
            RuntimeError: If unable to generate unique path after max retries
        """
        for attempt in range(max_retries):
            proposal_id = self._generate_proposal_id()
            proposal_path = self.proposals_dir / proposal_id

            if not proposal_path.exists():
                return proposal_id, proposal_path

            logger.warning(f"Proposal path collision on attempt {attempt + 1}: {proposal_path}")
            time.sleep(0.01)  # Small delay before retry

        raise RuntimeError(f"Failed to generate unique proposal path after {max_retries} attempts")

    def create_proposal(self, name: str, description: str, capabilities: List[str]) -> Dict:
        """
        Create a new agent proposal from template.

        Args:
            name: Agent name
            description: Agent description
            capabilities: List of declared capabilities

        Returns:
            Metadata dictionary with:
            - proposal_id: Unique proposal identifier
            - path: Path to proposal directory
            - name: Agent name
            - capabilities: List of capabilities
            - created_at: ISO timestamp

        Raises:
            FileNotFoundError: If template directory doesn't exist
            RuntimeError: If unable to create unique proposal
        """
        logger.info(f"Creating proposal: name='{name}', capabilities={capabilities}")

        # Validate template exists
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        # Generate unique proposal ID and path
        proposal_id, proposal_path = self._ensure_unique_proposal_path()

        created_at = datetime.now(timezone.utc).isoformat()

        try:
            # Copy template folder to proposal path
            logger.debug(f"Copying template from {self.template_dir} to {proposal_path}")
            shutil.copytree(self.template_dir, proposal_path)

            # Load agent.yaml
            agent_yaml_path = proposal_path / 'agent.yaml'

            if not agent_yaml_path.exists():
                raise FileNotFoundError(f"agent.yaml not found in template: {agent_yaml_path}")

            with open(agent_yaml_path, 'r') as f:
                agent_config = yaml.safe_load(f)

            # Update agent.yaml with proposal metadata
            agent_config['name'] = name
            agent_config['description'] = description
            agent_config['capabilities'] = capabilities
            agent_config['proposal_id'] = proposal_id
            agent_config['created_at'] = created_at

            # Write updated agent.yaml
            with open(agent_yaml_path, 'w') as f:
                yaml.safe_dump(agent_config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Proposal created successfully: {proposal_id} at {proposal_path}")

            return {
                'proposal_id': proposal_id,
                'path': str(proposal_path.resolve()),
                'name': name,
                'capabilities': capabilities,
                'created_at': created_at
            }

        except Exception as e:
            # Cleanup on failure
            if proposal_path.exists():
                logger.error(f"Cleaning up failed proposal: {proposal_path}")
                shutil.rmtree(proposal_path)

            logger.error(f"Failed to create proposal: {e}")
            raise


if __name__ == '__main__':
    # Test agent creation
    creator = AgentCreator()

    metadata = creator.create_proposal(
        name='test-agent',
        description='Test agent for validation',
        capabilities=['test', 'validation']
    )

    print(f"Created proposal: {metadata['proposal_id']}")
    print(f"Path: {metadata['path']}")
