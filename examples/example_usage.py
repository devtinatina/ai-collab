#!/usr/bin/env python3
"""Example usage of AI Collaboration Tool as a library"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_clients import create_client
from workflow import CollaborationWorkflow


def main():
    # Create AI clients
    manager = create_client(
        provider="openai",
        model="gpt-4o",
        temperature=0.3,
    )

    developer = create_client(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        temperature=0.7,
    )

    # Create workflow
    workflow = CollaborationWorkflow(
        manager_client=manager,
        developer_client=developer,
        max_iterations=5,
        output_dir="./output",
    )

    # Example 1: Development workflow
    print("\n=== Development Workflow ===\n")
    result = workflow.run_development(
        "Create a Python function that validates Korean phone numbers"
    )
    print(f"\nSuccess: {result.success}")
    print(f"Iterations: {result.iterations}")

    # Example 2: Code review workflow
    print("\n=== Code Review Workflow ===\n")
    sample_code = '''
def add_numbers(a, b):
    return a + b

def divide(a, b):
    return a / b
'''
    result = workflow.run_review(sample_code, "Basic math operations")
    print(f"\nSuccess: {result.success}")
    print(f"Iterations: {result.iterations}")

    # Example 3: Planning workflow
    print("\n=== Planning Workflow ===\n")
    result = workflow.run_planning(
        "Build a simple REST API with user authentication using FastAPI"
    )
    print(f"\nSuccess: {result.success}")
    print(f"Iterations: {result.iterations}")


if __name__ == "__main__":
    main()
