import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Task:
    id: str
    user_id: str
    description: str
    plan: Optional[List] = None
    status: str = "pending"
    assigned: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subtask:
    id: str
    description: str
    success_criteria: str
    estimated_model: str
    required_privileges: List[str]


class Planner:
    WORKER_PATTERNS = {
        "code_worker": r"\b(implement|code|build|develop|create.*file|write.*function|refactor|debug)\b",
        "math_worker": r"\b(calculate|compute|solve|equation|math|formula|algorithm)\b",
        "research_worker": r"\b(research|analyze|investigate|explore|find.*information|study|review)\b",
        "data_worker": r"\b(process.*data|transform|parse|extract|clean.*data|aggregate)\b",
    }

    PRIVILEGE_PATTERNS = {
        "filesystem": r"\b(file|directory|folder|read|write|save|load|create.*file|delete)\b",
        "network": r"\b(api|http|request|fetch|download|upload|call|endpoint)\b",
        "execute": r"\b(run|execute|invoke|launch|start|process)\b",
        "database": r"\b(database|query|sql|insert|update|select|db)\b",
    }

    def decompose_task(self, task: Task) -> List[Subtask]:
        """Decompose a task into 2-5 executable subtasks with assigned workers and privileges."""
        description = task.description.lower()

        subtasks_raw = self._split_into_subtasks(description)
        subtasks = []

        for idx, subtask_desc in enumerate(subtasks_raw):
            subtask_id = self._generate_subtask_id(task.id, idx)
            worker = self._analyze_task_type(subtask_desc)
            privileges = self._infer_privileges(subtask_desc)
            success_criteria = self._generate_success_criteria(subtask_desc)

            subtasks.append(Subtask(
                id=subtask_id,
                description=subtask_desc.strip(),
                success_criteria=success_criteria,
                estimated_model=worker,
                required_privileges=privileges
            ))

        return subtasks

    def _split_into_subtasks(self, description: str) -> List[str]:
        split_patterns = [
            r"\d+\.\s+",
            r"\bthen\b",
            r"\band then\b",
            r"\bafter that\b",
            r"\bnext\b",
            r",\s*and\s+",
        ]

        for pattern in split_patterns:
            parts = re.split(pattern, description, flags=re.IGNORECASE)
            if 2 <= len(parts) <= 5:
                return [p.strip() for p in parts if p.strip()]

        sentences = re.split(r'[.!;]\s+', description)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) >= 2:
            if len(sentences) > 5:
                step_size = len(sentences) // 3
                return [
                    " ".join(sentences[:step_size]),
                    " ".join(sentences[step_size:step_size*2]),
                    " ".join(sentences[step_size*2:])
                ]
            return sentences[:5]

        words = description.split()
        chunk_size = max(len(words) // 3, 5)
        return [
            " ".join(words[:chunk_size]),
            " ".join(words[chunk_size:chunk_size*2]),
            " ".join(words[chunk_size*2:])
        ]

    def _analyze_task_type(self, description: str) -> str:
        description_lower = description.lower()
        scores = {}

        for worker, pattern in self.WORKER_PATTERNS.items():
            if re.search(pattern, description_lower, re.IGNORECASE):
                scores[worker] = scores.get(worker, 0) + 1

        if scores:
            return max(scores, key=scores.get)
        return "code_worker"

    def _infer_privileges(self, description: str) -> List[str]:
        description_lower = description.lower()
        privileges = set()

        for privilege, pattern in self.PRIVILEGE_PATTERNS.items():
            if re.search(pattern, description_lower, re.IGNORECASE):
                privileges.add(privilege)

        if not privileges:
            privileges.add("execute")

        return sorted(list(privileges))

    def _generate_success_criteria(self, description: str) -> str:
        description_clean = description.strip().rstrip('.')

        if re.search(r"\b(implement|create|build|write)\b", description, re.IGNORECASE):
            return f"Successfully completed: {description_clean}"
        elif re.search(r"\b(test|verify|validate)\b", description, re.IGNORECASE):
            return f"All tests pass and verification complete"
        elif re.search(r"\b(analyze|research|investigate)\b", description, re.IGNORECASE):
            return f"Analysis complete with documented findings"
        else:
            return f"Task completed successfully: {description_clean}"

    def _generate_subtask_id(self, task_id: str, index: int) -> str:
        return f"{task_id}_sub_{index}_{uuid.uuid4().hex[:8]}"
