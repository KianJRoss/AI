# ProposalValidator Usage Guide

## Overview

`ProposalValidator` validates agent proposal folders created by `AgentCreator`. It ensures proposals have the correct structure and required metadata before they proceed to sandbox testing and registration.

## Location

**File:** `src/acp/validator.py`

## Class: ProposalValidator

### Initialization

```python
from acp.validator import ProposalValidator

validator = ProposalValidator()
```

No configuration required - the validator uses predefined validation rules.

## Main Method: validate_proposal()

### Signature

```python
def validate_proposal(path: str) -> dict
```

### Parameters

- **path** (str): Absolute or relative path to the proposal directory

### Return Value

Returns a dictionary with:

```python
{
    'valid': bool,        # True if all checks pass, False otherwise
    'errors': [str],      # List of error messages (failures)
    'warnings': [str]     # List of warning messages (non-critical)
}
```

### Validation Checks

#### 1. Path Existence
- Verifies the proposal path exists
- Confirms it's a directory (not a file)

**Errors:**
- `"Proposal path does not exist: {path}"`
- `"Proposal path is not a directory: {path}"`

#### 2. Required Files
Checks for presence of:
- `agent.yaml`
- `main.py`
- `tests/` (directory)

**Errors:**
- `"Missing required file/directory: {filename}"`

#### 3. agent.yaml Structure
Validates the YAML file contains required fields:
- `name` (non-empty string)
- `description` (non-empty string)
- `capabilities` (must be a list)
- `proposal_id` (non-empty string)
- `created_at` (non-empty string, ISO 8601 format)

**Errors:**
- `"Missing required YAML field: {field}"`
- `"Empty required YAML field: {field}"`
- `"Field 'capabilities' must be a list"`
- `"Invalid YAML syntax in agent.yaml: {error}"`
- `"Error reading agent.yaml: {error}"`

#### 4. Optional Fields (Warnings)
Checks for optional but recommended fields:
- `version`
- `entrypoint`
- `tests` (test file list)

**Warnings:**
- `"Optional field 'version' not specified"`
- `"Optional field 'entrypoint' not specified, defaulting to main.py"`
- `"Optional field 'tests' not specified"`

#### 5. Content Checks
- Verifies `main.py` is not empty
- Checks `tests/` directory contains at least one `test_*.py` file

**Warnings:**
- `"main.py is empty"`
- `"No test files found in tests/ directory"`
- `"Could not read main.py: {error}"`

## Usage Examples

### Example 1: Basic Validation

```python
from acp.validator import ProposalValidator

validator = ProposalValidator()
result = validator.validate_proposal('proposals/proposal-20251130-abc123')

if result['valid']:
    print("Proposal is valid!")
    print(f"Warnings: {result['warnings']}")
else:
    print("Validation failed!")
    print(f"Errors: {result['errors']}")
```

### Example 2: Integration with AgentCreator

```python
from acp.creator import AgentCreator
from acp.validator import ProposalValidator

# Create proposal
creator = AgentCreator()
metadata = creator.create_proposal(
    name='data-processor',
    description='Processes data streams',
    capabilities=['data', 'processing']
)

# Validate immediately
validator = ProposalValidator()
result = validator.validate_proposal(metadata['path'])

if not result['valid']:
    print(f"Proposal invalid: {result['errors']}")
    exit(1)

print(f"Proposal {metadata['proposal_id']} is valid!")
```

### Example 3: Conditional Processing

```python
from acp.validator import ProposalValidator

validator = ProposalValidator()
result = validator.validate_proposal('proposals/my-agent')

# Process based on validation result
if result['valid']:
    if len(result['warnings']) > 0:
        print(f"Valid with warnings: {result['warnings']}")
        # Proceed with caution
    else:
        print("Perfect proposal - no issues!")
        # Proceed normally
else:
    print("Validation failed - cannot proceed")
    for error in result['errors']:
        print(f"  - {error}")
    # Reject proposal
```

### Example 4: Batch Validation

```python
from pathlib import Path
from acp.validator import ProposalValidator

validator = ProposalValidator()
proposals_dir = Path('proposals')

results = {}

for proposal_dir in proposals_dir.iterdir():
    if proposal_dir.is_dir():
        result = validator.validate_proposal(str(proposal_dir))
        results[proposal_dir.name] = result

# Summary
valid_count = sum(1 for r in results.values() if r['valid'])
print(f"Valid proposals: {valid_count}/{len(results)}")

# Show invalid proposals
for name, result in results.items():
    if not result['valid']:
        print(f"\n{name}:")
        for error in result['errors']:
            print(f"  - {error}")
```

## Bonus Method: validate_yaml_only()

For cases where you only need to validate the YAML file:

```python
validator = ProposalValidator()
result = validator.validate_yaml_only('proposals/my-agent/agent.yaml')

if result['valid']:
    print("YAML is valid")
else:
    print(f"YAML errors: {result['errors']}")
```

## Integration with Coordinator Workflow

```python
from acp.creator import AgentCreator
from acp.validator import ProposalValidator
from acp.registrar import AgentRegistrar
from sandbox.ci import CIManager
from coordinator.policy_engine import PolicyEngine

# Step 1: Create proposal
creator = AgentCreator()
metadata = creator.create_proposal(
    name="sentiment-analyzer",
    description="Analyzes text sentiment",
    capabilities=["nlp", "sentiment"]
)

# Step 2: Validate structure
validator = ProposalValidator()
validation = validator.validate_proposal(metadata['path'])

if not validation['valid']:
    print(f"Structural validation failed: {validation['errors']}")
    exit(1)

# Step 3: Run sandbox tests
ci = CIManager()
sandbox_result = ci.submit_proposal(metadata['path'])

if not sandbox_result['policy_summary']['tests_passed']:
    print("Sandbox tests failed")
    exit(1)

# Step 4: Policy evaluation
policy_engine = PolicyEngine()
context = {
    'sandbox_tests_passed': True,
    'anomaly_flags': sandbox_result['policy_summary']['anomaly_flags']
}

policy_decision = policy_engine.evaluate(
    action={'type': 'promote_agent', 'subject': metadata['proposal_id']},
    context=context
)

# Step 5: Register if approved
if policy_decision['decision'] == 'auto_allow':
    registrar = AgentRegistrar()
    reg_result = registrar.register_agent(metadata['path'])
    print(f"Agent registered: {reg_result['entry']['name']}")
else:
    print(f"Escalating for review: {policy_decision['reasons']}")
```

## Error Handling

```python
from acp.validator import ProposalValidator

validator = ProposalValidator()

try:
    result = validator.validate_proposal('/some/path')

    if not result['valid']:
        # Handle validation failure
        for error in result['errors']:
            log_error(f"Validation error: {error}")

        # Optionally send notification
        notify_admin(f"Proposal validation failed: {result['errors']}")

except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected validation error: {e}")
```

## Best Practices

1. **Always validate before sandbox testing**
   ```python
   # Validate structure first (fast)
   if not validator.validate_proposal(path)['valid']:
       return  # Don't waste time on invalid proposals

   # Then run expensive sandbox tests
   sandbox_result = ci.submit_proposal(path)
   ```

2. **Log warnings even if valid**
   ```python
   result = validator.validate_proposal(path)

   if result['valid'] and result['warnings']:
       logger.warning(f"Proposal {path} valid but has warnings: {result['warnings']}")
   ```

3. **Provide clear feedback to users**
   ```python
   result = validator.validate_proposal(path)

   if not result['valid']:
       print("Proposal validation failed:")
       for i, error in enumerate(result['errors'], 1):
           print(f"  {i}. {error}")

       print("\nPlease fix these issues and try again.")
   ```

4. **Use early returns for efficiency**
   ```python
   result = validator.validate_proposal(path)

   if not result['valid']:
       return {'status': 'rejected', 'reason': result['errors']}

   # Continue with expensive operations...
   ```

## Validation Summary

### What Gets Validated

✅ Path existence and type
✅ Required files (agent.yaml, main.py, tests/)
✅ YAML syntax
✅ Required YAML fields (name, description, capabilities, proposal_id, created_at)
✅ Field types (capabilities must be list)
✅ Empty field detection
✅ Test file presence
✅ Optional field recommendations

### What Doesn't Get Validated

❌ Code quality (use static analysis tools)
❌ Test correctness (use sandbox runner)
❌ Security issues (use dangerous code scanner)
❌ Capability semantics (future enhancement)
❌ Code functionality (use sandbox execution)

## Performance

- **Fast:** ~5-10ms per proposal (filesystem I/O only)
- **No external dependencies:** Pure Python with PyYAML
- **No network calls:** All checks are local
- **Scales well:** Can validate hundreds of proposals per second

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'acp'"

**Solution:**
```bash
# Install package in development mode
pip install -e .
```

### Issue: "Invalid YAML syntax"

**Solution:** Check agent.yaml for:
- Proper indentation (use spaces, not tabs)
- Quoted strings with special characters
- Valid YAML structure

### Issue: "No test files found"

**Solution:** Ensure test files in `tests/` directory:
- Follow naming convention: `test_*.py`
- At least one test file required
- Tests can be empty (warning) but must exist

## Command-Line Usage

Run validator directly from command line:

```bash
python src/acp/validator.py proposals/proposal-20251130-abc123
```

Output:
```
Valid: True
Errors: []
Warnings: ['Optional field 'version' not specified']
```

## Summary

`ProposalValidator` provides:
- ✅ Fast structural validation
- ✅ Comprehensive error reporting
- ✅ Warning system for best practices
- ✅ Integration-ready for Coordinator workflow
- ✅ Command-line and programmatic access
- ✅ No external dependencies beyond PyYAML

It's a critical component in the ACP pipeline, ensuring only well-formed proposals proceed to expensive sandbox testing and registration.
