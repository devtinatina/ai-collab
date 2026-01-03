"""Collaboration workflow engine - Agile-style AI collaboration"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ai_clients import AIClient, Message, create_client
from prompts import (
    MANAGER_SYSTEM_PROMPT,
    MANAGER_REVIEW_PROMPT,
    MANAGER_PLANNING_PROMPT,
    DEVELOPER_SYSTEM_PROMPT,
    DEVELOPER_IMPLEMENT_PROMPT,
    DEVELOPER_REVISE_PROMPT,
    DEVELOPER_PLAN_PROMPT,
)


class WorkflowPhase(Enum):
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    APPROVED = "approved"


class TaskType(Enum):
    CODE_DEVELOPMENT = "code_development"
    CODE_REVIEW = "code_review"
    PROJECT_PLANNING = "project_planning"
    DOCUMENTATION = "documentation"


@dataclass
class ConversationTurn:
    role: str  # "manager" or "developer"
    content: str
    phase: WorkflowPhase
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WorkflowResult:
    success: bool
    final_output: str
    conversation_history: list[ConversationTurn]
    iterations: int
    phase: WorkflowPhase


class CollaborationWorkflow:
    """Main workflow engine for AI collaboration"""

    def __init__(
        self,
        manager_client: AIClient,
        developer_client: AIClient,
        max_iterations: int = 10,
        output_dir: str = "./output",
        on_message: Callable[[str, str, str], None] = None,
    ):
        self.manager = manager_client
        self.developer = developer_client
        self.max_iterations = max_iterations
        self.output_dir = output_dir
        self.console = Console()
        self.on_message = on_message  # Callback for each message
        self.conversation_history: list[ConversationTurn] = []

    def _display_message(self, role: str, content: str, phase: str):
        """Display a message in the console"""
        colors = {"manager": "red", "developer": "green", "system": "blue"}
        titles = {"manager": "PM (Manager)", "developer": "Developer", "system": "System"}

        self.console.print(
            Panel(
                Markdown(content),
                title=f"[bold {colors.get(role, 'white')}]{titles.get(role, role)}[/]",
                subtitle=f"[dim]{phase}[/]",
                border_style=colors.get(role, "white"),
            )
        )

        if self.on_message:
            self.on_message(role, content, phase)

    def _add_turn(self, role: str, content: str, phase: WorkflowPhase):
        """Add a conversation turn"""
        turn = ConversationTurn(role=role, content=content, phase=phase)
        self.conversation_history.append(turn)
        self._display_message(role, content, phase.value)

    def _check_approval(self, response: str) -> bool:
        """Check if the manager approved"""
        return "[APPROVED]" in response.upper()

    def run_development(self, requirements: str) -> WorkflowResult:
        """Run a full development workflow"""
        self.conversation_history = []
        current_phase = WorkflowPhase.PLANNING

        self._display_message("system", f"Starting development workflow...\n\n**Requirements:**\n{requirements}", "start")

        # Phase 1: Developer creates initial plan
        plan_prompt = DEVELOPER_PLAN_PROMPT.format(requirements=requirements)
        developer_plan = self.developer.chat(
            [Message(role="user", content=plan_prompt)],
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
        )
        self._add_turn("developer", developer_plan, current_phase)

        # Phase 2: Manager reviews plan
        review_prompt = MANAGER_PLANNING_PROMPT.format(
            requirements=requirements, plan=developer_plan
        )
        manager_feedback = self.manager.chat(
            [Message(role="user", content=review_prompt)],
            system_prompt=MANAGER_SYSTEM_PROMPT,
        )
        self._add_turn("manager", manager_feedback, current_phase)

        # Phase 3: Implementation loop
        current_phase = WorkflowPhase.IMPLEMENTATION
        previous_submission = developer_plan
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # Developer implements/revises
            if iterations == 1:
                impl_prompt = DEVELOPER_IMPLEMENT_PROMPT.format(
                    requirements=requirements, instructions=manager_feedback
                )
            else:
                impl_prompt = DEVELOPER_REVISE_PROMPT.format(
                    requirements=requirements,
                    previous_submission=previous_submission,
                    feedback=manager_feedback,
                )

            developer_response = self.developer.chat(
                [Message(role="user", content=impl_prompt)],
                system_prompt=DEVELOPER_SYSTEM_PROMPT,
            )
            self._add_turn("developer", developer_response, current_phase)
            previous_submission = developer_response

            # Manager reviews
            current_phase = WorkflowPhase.REVIEW
            review_prompt = MANAGER_REVIEW_PROMPT.format(
                task_type="implementation",
                requirements=requirements,
                submission=developer_response,
            )
            manager_feedback = self.manager.chat(
                [Message(role="user", content=review_prompt)],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                break

            current_phase = WorkflowPhase.IMPLEMENTATION

        # Save results
        self._save_result(requirements, previous_submission)

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_submission,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
        )

    def run_review(self, code: str, context: str = "") -> WorkflowResult:
        """Run a code review workflow"""
        self.conversation_history = []
        current_phase = WorkflowPhase.REVIEW

        review_request = f"다음 코드를 리뷰해주세요:\n\n{code}"
        if context:
            review_request += f"\n\n컨텍스트: {context}"

        self._display_message("system", f"Starting code review...", "start")

        # Manager does initial review
        manager_review = self.manager.chat(
            [Message(role="user", content=review_request)],
            system_prompt=MANAGER_SYSTEM_PROMPT,
        )
        self._add_turn("manager", manager_review, current_phase)

        # Developer responds with improvements
        developer_response = self.developer.chat(
            [
                Message(role="user", content=f"PM의 코드 리뷰 피드백입니다:\n\n{manager_review}\n\n원본 코드:\n{code}\n\n피드백을 반영하여 개선된 코드를 제출해주세요.")
            ],
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
        )
        self._add_turn("developer", developer_response, current_phase)

        iterations = 1
        previous_submission = developer_response

        while iterations < self.max_iterations:
            iterations += 1

            # Manager re-reviews
            final_review = self.manager.chat(
                [Message(role="user", content=f"개발자가 수정한 코드입니다:\n\n{previous_submission}\n\n다시 검토해주세요.")],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._add_turn("manager", final_review, current_phase)

            if self._check_approval(final_review):
                current_phase = WorkflowPhase.APPROVED
                break

            # Developer revises again
            developer_response = self.developer.chat(
                [Message(role="user", content=f"PM의 추가 피드백:\n\n{final_review}\n\n이전 제출물:\n{previous_submission}\n\n다시 수정해주세요.")],
                system_prompt=DEVELOPER_SYSTEM_PROMPT,
            )
            self._add_turn("developer", developer_response, current_phase)
            previous_submission = developer_response

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_submission,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
        )

    def run_planning(self, project_description: str) -> WorkflowResult:
        """Run a project planning workflow"""
        self.conversation_history = []
        current_phase = WorkflowPhase.PLANNING

        self._display_message("system", f"Starting project planning...\n\n**Project:**\n{project_description}", "start")

        iterations = 0
        previous_plan = ""

        while iterations < self.max_iterations:
            iterations += 1

            # Developer creates/revises plan
            if iterations == 1:
                plan_prompt = DEVELOPER_PLAN_PROMPT.format(requirements=project_description)
            else:
                plan_prompt = f"PM 피드백을 반영하여 계획을 수정해주세요:\n\n피드백:\n{manager_feedback}\n\n이전 계획:\n{previous_plan}"

            developer_plan = self.developer.chat(
                [Message(role="user", content=plan_prompt)],
                system_prompt=DEVELOPER_SYSTEM_PROMPT,
            )
            self._add_turn("developer", developer_plan, current_phase)
            previous_plan = developer_plan

            # Manager reviews plan
            review_prompt = MANAGER_PLANNING_PROMPT.format(
                requirements=project_description, plan=developer_plan
            )
            manager_feedback = self.manager.chat(
                [Message(role="user", content=review_prompt)],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                break

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_plan,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
        )

    def run_documentation(self, topic: str, context: str = "") -> WorkflowResult:
        """Run a documentation workflow"""
        self.conversation_history = []
        current_phase = WorkflowPhase.IMPLEMENTATION

        doc_request = f"다음 주제에 대한 문서를 작성해주세요: {topic}"
        if context:
            doc_request += f"\n\n참고 컨텍스트:\n{context}"

        self._display_message("system", f"Starting documentation...\n\n**Topic:**\n{topic}", "start")

        iterations = 0
        previous_doc = ""

        while iterations < self.max_iterations:
            iterations += 1

            # Developer writes/revises doc
            if iterations == 1:
                developer_doc = self.developer.chat(
                    [Message(role="user", content=doc_request)],
                    system_prompt=DEVELOPER_SYSTEM_PROMPT + "\n\n문서 작성 시 명확하고 구조화된 형식을 사용하세요.",
                )
            else:
                developer_doc = self.developer.chat(
                    [Message(role="user", content=f"PM 피드백을 반영하여 문서를 수정해주세요:\n\n피드백:\n{manager_feedback}\n\n이전 문서:\n{previous_doc}")],
                    system_prompt=DEVELOPER_SYSTEM_PROMPT,
                )

            self._add_turn("developer", developer_doc, current_phase)
            previous_doc = developer_doc

            # Manager reviews
            current_phase = WorkflowPhase.REVIEW
            manager_feedback = self.manager.chat(
                [Message(role="user", content=f"다음 문서를 검토해주세요:\n\n주제: {topic}\n\n문서:\n{developer_doc}")],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                break

            current_phase = WorkflowPhase.IMPLEMENTATION

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_doc,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
        )

    def _save_result(self, requirements: str, output: str):
        """Save the result to a file"""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"result_{timestamp}.md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# AI Collaboration Result\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write(f"## Requirements\n\n{requirements}\n\n")
            f.write(f"## Final Output\n\n{output}\n\n")
            f.write(f"## Conversation History\n\n")
            for turn in self.conversation_history:
                f.write(f"### {turn.role.upper()} ({turn.phase.value})\n\n")
                f.write(f"{turn.content}\n\n---\n\n")

        self.console.print(f"\n[dim]Result saved to: {filename}[/]")
