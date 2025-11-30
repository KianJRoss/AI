from planner import Planner, Task


def test_planner():
    planner = Planner()

    task1 = Task(
        id="task_001",
        user_id="user_123",
        description="Implement a REST API endpoint, then write unit tests, and finally deploy to production"
    )

    subtasks1 = planner.decompose_task(task1)
    print(f"Task 1: {task1.description}")
    print(f"Decomposed into {len(subtasks1)} subtasks:\n")
    for st in subtasks1:
        print(f"  ID: {st.id}")
        print(f"  Description: {st.description}")
        print(f"  Model: {st.estimated_model}")
        print(f"  Privileges: {st.required_privileges}")
        print(f"  Success: {st.success_criteria}\n")

    task2 = Task(
        id="task_002",
        user_id="user_456",
        description="Research the latest trends in quantum computing and analyze their potential applications"
    )

    subtasks2 = planner.decompose_task(task2)
    print(f"\nTask 2: {task2.description}")
    print(f"Decomposed into {len(subtasks2)} subtasks:\n")
    for st in subtasks2:
        print(f"  ID: {st.id}")
        print(f"  Description: {st.description}")
        print(f"  Model: {st.estimated_model}")
        print(f"  Privileges: {st.required_privileges}")
        print(f"  Success: {st.success_criteria}\n")

    task3 = Task(
        id="task_003",
        user_id="user_789",
        description="Calculate the average response time from API logs and generate a performance report"
    )

    subtasks3 = planner.decompose_task(task3)
    print(f"\nTask 3: {task3.description}")
    print(f"Decomposed into {len(subtasks3)} subtasks:\n")
    for st in subtasks3:
        print(f"  ID: {st.id}")
        print(f"  Description: {st.description}")
        print(f"  Model: {st.estimated_model}")
        print(f"  Privileges: {st.required_privileges}")
        print(f"  Success: {st.success_criteria}\n")

    assert 2 <= len(subtasks1) <= 5, "Subtask count out of range"
    assert 2 <= len(subtasks2) <= 5, "Subtask count out of range"
    assert 2 <= len(subtasks3) <= 5, "Subtask count out of range"

    print("All tests passed!")


if __name__ == "__main__":
    test_planner()
