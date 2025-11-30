# Agent Creation Pipeline (ACP)

Scaffolding subsystem for creating, validating, and registering agent proposals.

## Overview

The ACP provides the Coordinator with:
1. Agent proposal generation from templates
2. Proposal structure validation
3. Agent registry management
4. Integration with Sandbox & CI for testing

**Note:** This is pure scaffolding - no LLM integration yet.

## Architecture

```
agents/
├── registry.json           # Registered agents metadata
└── templates/
    └── base_agent/         # Template for new agents
        ├── agent.yaml
        ├── main.py
        └── tests/test_basic.py

proposals/
└── <proposal-id>/          # Generated proposal directories

src/acp/
├── creator.py              # AgentCreator - generates proposals
├── validator.py            # ProposalValidator - validates structure
└── registrar.py            # AgentRegistrar - manages registry
```

## Components

### AgentCreator (`creator.py`)

Generates agent proposals from templates.

**Usage:**

```python
from acp.creator import AgentCreator

creator = AgentCreator()

metadata = creator.create_proposal(
    name='graph-analyzer',
    description='Extracts graph structure from data',
    capabilities=['graph', 'analysis']
)

print(f"Created: {metadata['proposal_id']}")
print(f"Path: {metadata['path']}")
```

**Proposal ID Format:** `proposal-<timestamp>-<random4chars>`

Example: `proposal-20251130120000-a7b3`

**Returns:**

```python
{
    'proposal_id': str,
    'path': str,              # Absolute path to proposal directory
    'name': str,
    'capabilities': list,
    'created_at': str         # ISO 8601 timestamp
}
```

**Features:**
- Atomic proposal creation with automatic retry on collision
- Copies template directory to `proposals/<id>/`
- Updates `agent.yaml` with proposal metadata
- Cleanup on failure

### ProposalValidator (`validator.py`)

Validates agent proposal structure and metadata.

**Usage:**

```python
from acp.validator import ProposalValidator

validator = ProposalValidator()

result = validator.validate_proposal('proposals/proposal-xyz')

if result['valid']:
    print("Proposal is valid")
else:
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
```

**Validation Checks:**

Required files:
- `agent.yaml`
- `main.py`
- `tests/` directory

Required YAML fields:
- `name`
- `description`
- `capabilities` (must be list)
- `proposal_id`
- `created_at`

**Returns:**

```python
{
    'valid': bool,
    'errors': [str],          # Critical issues
    'warnings': [str]         # Non-critical issues
}
```

### AgentRegistrar (`registrar.py`)

Manages agent registration in `agents/registry.json`.

**Usage:**

```python
from acp.registrar import AgentRegistrar

registrar = AgentRegistrar()

# Register approved proposal
result = registrar.register_agent('proposals/proposal-xyz')

if result['registered']:
    print(f"Registered: {result['entry']['name']}")
else:
    print(f"Error: {result['error']}")

# Query registry
all_agents = registrar.get_registry()
agent = registrar.get_agent_by_id('proposal-xyz')
graph_agents = registrar.get_agents_by_capability('graph')
```

**Registry Entry Format:**

```python
{
    'name': str,
    'id': str,                # proposal_id
    'description': str,
    'capabilities': list,
    'added_at': str,          # ISO 8601 timestamp
    'path': str               # Absolute path to proposal
}
```

**Registry File:** `agents/registry.json` (JSON Lines format)

**Features:**
- Creates registry if doesn't exist
- Allows duplicate registrations (doesn't merge)
- Supports pre-loaded YAML dict
- Query by ID or capability

## Integration with Coordinator

Example workflow:

```python
from acp.creator import AgentCreator
from acp.validator import ProposalValidator
from acp.registrar import AgentRegistrar
from sandbox.ci import CIManager
from coordinator.policy_engine import PolicyEngine

# 1. Create proposal
creator = AgentCreator()
metadata = creator.create_proposal(
    name="graph-analyzer",
    description="Extracts graph structure",
    capabilities=["graph", "analysis"]
)

# 2. Validate structure
validator = ProposalValidator()
validation = validator.validate_proposal(metadata['path'])

if not validation['valid']:
    print(f"Validation failed: {validation['errors']}")
    exit(1)

# 3. Run sandbox tests
ci = CIManager()
sandbox_result = ci.submit_proposal(metadata['path'])

# 4. Policy evaluation
policy_engine = PolicyEngine()
context = {
    'sandbox_tests_passed': sandbox_result['policy_summary']['tests_passed'],
    'anomaly_flags': sandbox_result['policy_summary']['anomaly_flags']
}

policy_decision = policy_engine.evaluate(
    action={'type': 'promote_agent', 'subject': metadata['proposal_id']},
    context=context
)

# 5. Register if approved
if policy_decision['decision'] == 'auto_allow':
    registrar = AgentRegistrar()
    reg_result = registrar.register_agent(metadata['path'])
    print(f"Agent registered: {reg_result['entry']['name']}")
else:
    print(f"Escalating for review: {policy_decision['reasons']}")
```

## Base Agent Template

The base agent template (`agents/templates/base_agent/`) provides:

**agent.yaml:**
- Standard metadata fields
- Capability declarations
- Test specifications
- Entrypoint definition

**main.py:**
- `Agent` class with `execute()` and `validate_task()` methods
- Logging setup
- Entry point function

**tests/test_basic.py:**
- Basic initialization test
- Execution test
- Validation test

## Testing

Manual integration test:

```bash
python manual_test_runner.py
```

Output:
```
Testing AgentCreator...
  [OK] Created proposal: proposal-20251130120000-xyz
  [OK] Validation passed
  [OK] Registration successful
[SUCCESS] All ACP components working!
```

## Example: Creating a Custom Agent

1. **Create proposal:**

```python
creator = AgentCreator()
metadata = creator.create_proposal(
    name='sentiment-analyzer',
    description='Analyzes sentiment in text',
    capabilities=['nlp', 'sentiment']
)
```

2. **Customize the generated files in `proposals/<id>/`:**

Edit `main.py`:
```python
class Agent:
    def execute(self, task: dict) -> dict:
        text = task['text']
        # Custom sentiment analysis logic
        sentiment = analyze_sentiment(text)
        return {'success': True, 'sentiment': sentiment}
```

Edit `tests/test_basic.py`:
```python
def test_sentiment_analysis():
    agent = Agent()
    result = agent.execute({'text': 'I love this!'})
    assert result['sentiment'] == 'positive'
```

3. **Validate:**

```python
validator = ProposalValidator()
result = validator.validate_proposal(metadata['path'])
assert result['valid']
```

4. **Run sandbox tests:**

```python
ci = CIManager()
sandbox_result = ci.submit_proposal(metadata['path'])
assert sandbox_result['policy_summary']['tests_passed']
```

5. **Register:**

```python
registrar = AgentRegistrar()
reg_result = registrar.register_agent(metadata['path'])
print(f"Registered: {reg_result['entry']['id']}")
```

## Performance

**Benchmarks (Python 3.13, Windows):**
- Proposal creation: ~10-20ms
- Validation: ~5-10ms
- Registration: ~2-5ms
- End-to-end (create + validate + register): ~20-40ms

**Note:** Overhead is minimal; most time spent in filesystem I/O.

## Platform Compatibility

- **Python:** 3.11+
- **Platforms:** Windows, Linux, macOS
- **Dependencies:** PyYAML

## Future Enhancements

1. **LLM Integration**
   - Auto-generate agent code from natural language descriptions
   - Code review and improvement suggestions
   - Test generation

2. **Advanced Validation**
   - Semantic analysis of agent capabilities
   - Dependency conflict detection
   - Security pattern scanning

3. **Versioning**
   - Agent version tracking
   - Upgrade/downgrade support
   - Compatibility checking

4. **Templates**
   - Multiple agent templates (web scraper, data processor, etc.)
   - Template inheritance
   - Custom template creation

5. **Metrics**
   - Proposal success rate tracking
   - Agent performance monitoring
   - Registry analytics
