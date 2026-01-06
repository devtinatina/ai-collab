"""Collaboration workflow engine - Agile-style AI collaboration"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
from difflib import SequenceMatcher

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm

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
    total_tokens: int = 0
    total_cost: float = 0.0
    stopped_reason: str = ""  # "approved", "max_iterations", "max_tokens", "max_cost", "no_progress", "user_stopped"


class CollaborationWorkflow:
    """Main workflow engine for AI collaboration"""

    def __init__(
        self,
        manager_client: AIClient,
        developer_client: AIClient,
        max_iterations: int = 10,
        output_dir: str = "./output",
        on_message: Callable[[str, str, str], None] = None,
        # Advanced control parameters
        max_tokens: int = None,
        max_cost: float = None,
        checkpoint_interval: int = None,
        max_no_progress: int = 3,
        early_stop_similarity: float = 0.95,
        budget_mode: str = "balanced",
    ):
        self.manager = manager_client
        self.developer = developer_client
        self.console = Console()
        self.on_message = on_message
        self.conversation_history: list[ConversationTurn] = []
        self.output_dir = output_dir

        # Budget mode presets
        self.budget_mode = budget_mode
        self._apply_budget_mode(budget_mode, max_iterations, max_tokens, max_cost, checkpoint_interval)

        # Advanced controls
        self.max_no_progress = max_no_progress
        self.early_stop_similarity = early_stop_similarity

        # Tracking variables
        self.total_tokens = 0
        self.total_cost = 0.0
        self.no_progress_count = 0
        self.previous_submission_text = None

    def _apply_budget_mode(self, mode: str, max_iter, max_tok, max_c, checkpoint):
        """Apply budget mode presets"""
        presets = {
            "economy": {
                "max_iterations": 5,
                "max_tokens": 30000,
                "max_cost": 1.0,
                "checkpoint_interval": 3,
            },
            "balanced": {
                "max_iterations": 10,
                "max_tokens": 50000,
                "max_cost": 2.0,
                "checkpoint_interval": 5,
            },
            "quality": {
                "max_iterations": 15,
                "max_tokens": 100000,
                "max_cost": 5.0,
                "checkpoint_interval": 7,
            },
        }

        preset = presets.get(mode, presets["balanced"])

        # Use explicit parameters if provided, otherwise use preset
        self.max_iterations = max_iter if max_iter != 10 else preset["max_iterations"]
        self.max_tokens = max_tok if max_tok is not None else preset["max_tokens"]
        self.max_cost = max_c if max_c is not None else preset["max_cost"]
        self.checkpoint_interval = checkpoint if checkpoint is not None else preset["checkpoint_interval"]

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

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens (1 token ≈ 4 characters)"""
        return len(text) // 4

    def _estimate_cost(self, tokens: int, provider: str, model: str) -> float:
        """Estimate API cost based on tokens"""
        # Rough estimates (per 1M tokens)
        cost_map = {
            "openai": {"gpt-4o": 2.5, "gpt-5.1-codex-mini": 1.0, "o1-mini": 3.0},
            "anthropic": {
                "claude-sonnet-4-20250514": 3.0,
                "claude-opus-4-20250514": 15.0,
            },
        }

        rate = cost_map.get(provider, {}).get(model, 2.0)
        return (tokens / 1_000_000) * rate

    def _track_usage(self, text: str, client: AIClient):
        """Track token usage and cost"""
        tokens = self._estimate_tokens(text)
        self.total_tokens += tokens

        provider = getattr(client, "provider", "unknown")
        model = getattr(client, "model", "unknown")
        cost = self._estimate_cost(tokens, provider, model)
        self.total_cost += cost

    def _check_budget_limits(self) -> tuple[bool, str]:
        """Check if budget limits exceeded"""
        if self.max_tokens and self.total_tokens >= self.max_tokens:
            return True, "max_tokens"
        if self.max_cost and self.total_cost >= self.max_cost:
            return True, "max_cost"
        return False, ""

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()

    def _check_progress(self, current_submission: str) -> bool:
        """Check if there's meaningful progress"""
        if self.previous_submission_text is None:
            self.previous_submission_text = current_submission
            return True

        similarity = self._calculate_similarity(self.previous_submission_text, current_submission)

        if similarity >= self.early_stop_similarity:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        self.previous_submission_text = current_submission
        return self.no_progress_count < self.max_no_progress

    def _user_checkpoint(self, iterations: int) -> bool:
        """Ask user if they want to continue"""
        if self.checkpoint_interval and iterations % self.checkpoint_interval == 0:
            self.console.print(f"\n[yellow]━━━ Checkpoint at iteration {iterations} ━━━[/yellow]")
            self.console.print(f"[dim]Tokens used: {self.total_tokens:,} / {self.max_tokens:,}[/dim]")
            self.console.print(f"[dim]Estimated cost: ${self.total_cost:.4f} / ${self.max_cost:.2f}[/dim]")

            return Confirm.ask("\nContinue workflow?", default=True)
        return True

    def _display_budget_status(self):
        """Display current budget status"""
        token_pct = (self.total_tokens / self.max_tokens * 100) if self.max_tokens else 0
        cost_pct = (self.total_cost / self.max_cost * 100) if self.max_cost else 0

        status = f"[dim]Budget: {self.total_tokens:,}/{self.max_tokens:,} tokens ({token_pct:.1f}%) | ${self.total_cost:.4f}/${self.max_cost:.2f} ({cost_pct:.1f}%)[/dim]"
        self.console.print(status)

    def run_development(self, requirements: str) -> WorkflowResult:
        """Run a full development workflow"""
        self.conversation_history = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.no_progress_count = 0
        self.previous_submission_text = None
        current_phase = WorkflowPhase.PLANNING
        stopped_reason = ""

        self._display_message("system", f"Starting development workflow (Mode: {self.budget_mode})...\n\n**Requirements:**\n{requirements}", "start")

        # Phase 1: Developer creates initial plan
        plan_prompt = DEVELOPER_PLAN_PROMPT.format(requirements=requirements)
        developer_plan = self.developer.chat(
            [Message(role="user", content=plan_prompt)],
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
        )
        self._track_usage(plan_prompt + developer_plan, self.developer)
        self._add_turn("developer", developer_plan, current_phase)

        # Phase 2: Manager reviews plan
        review_prompt = MANAGER_PLANNING_PROMPT.format(
            requirements=requirements, plan=developer_plan
        )
        manager_feedback = self.manager.chat(
            [Message(role="user", content=review_prompt)],
            system_prompt=MANAGER_SYSTEM_PROMPT,
        )
        self._track_usage(review_prompt + manager_feedback, self.manager)
        self._add_turn("manager", manager_feedback, current_phase)

        # Phase 3: Implementation loop
        current_phase = WorkflowPhase.IMPLEMENTATION
        previous_submission = developer_plan
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1
            self._display_budget_status()

            # Check budget limits
            exceeded, reason = self._check_budget_limits()
            if exceeded:
                stopped_reason = reason
                self.console.print(f"\n[red]⚠ Budget limit exceeded: {reason}[/red]")
                break

            # User checkpoint
            if not self._user_checkpoint(iterations):
                stopped_reason = "user_stopped"
                self.console.print("\n[yellow]Workflow stopped by user[/yellow]")
                break

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
            self._track_usage(impl_prompt + developer_response, self.developer)
            self._add_turn("developer", developer_response, current_phase)
            previous_submission = developer_response

            # Check progress
            if not self._check_progress(developer_response):
                stopped_reason = "no_progress"
                self.console.print(f"\n[yellow]⚠ No meaningful progress detected for {self.max_no_progress} iterations. Stopping.[/yellow]")
                break

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
            self._track_usage(review_prompt + manager_feedback, self.manager)
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                stopped_reason = "approved"
                break

            current_phase = WorkflowPhase.IMPLEMENTATION

        if not stopped_reason:
            stopped_reason = "max_iterations"

        # Display final stats
        self.console.print(f"\n[bold]Final Statistics:[/bold]")
        self.console.print(f"  Iterations: {iterations}")
        self.console.print(f"  Total tokens: {self.total_tokens:,}")
        self.console.print(f"  Estimated cost: ${self.total_cost:.4f}")
        self.console.print(f"  Stop reason: {stopped_reason}")

        # Save results
        self._save_result(requirements, previous_submission)

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_submission,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
            total_tokens=self.total_tokens,
            total_cost=self.total_cost,
            stopped_reason=stopped_reason,
        )

    def run_review(self, code: str, context: str = "") -> WorkflowResult:
        """Run a code review workflow"""
        self.conversation_history = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.no_progress_count = 0
        self.previous_submission_text = None
        current_phase = WorkflowPhase.REVIEW
        stopped_reason = ""

        review_request = f"다음 코드를 리뷰해주세요:\n\n{code}"
        if context:
            review_request += f"\n\n컨텍스트: {context}"

        self._display_message("system", f"Starting code review (Mode: {self.budget_mode})...", "start")

        # Manager does initial review
        manager_review = self.manager.chat(
            [Message(role="user", content=review_request)],
            system_prompt=MANAGER_SYSTEM_PROMPT,
        )
        self._track_usage(review_request + manager_review, self.manager)
        self._add_turn("manager", manager_review, current_phase)

        # Developer responds with improvements
        dev_prompt = f"PM의 코드 리뷰 피드백입니다:\n\n{manager_review}\n\n원본 코드:\n{code}\n\n피드백을 반영하여 개선된 코드를 제출해주세요."
        developer_response = self.developer.chat(
            [Message(role="user", content=dev_prompt)],
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
        )
        self._track_usage(dev_prompt + developer_response, self.developer)
        self._add_turn("developer", developer_response, current_phase)

        iterations = 1
        previous_submission = developer_response

        while iterations < self.max_iterations:
            iterations += 1
            self._display_budget_status()

            # Check budget limits
            exceeded, reason = self._check_budget_limits()
            if exceeded:
                stopped_reason = reason
                self.console.print(f"\n[red]⚠ Budget limit exceeded: {reason}[/red]")
                break

            # User checkpoint
            if not self._user_checkpoint(iterations):
                stopped_reason = "user_stopped"
                break

            # Manager re-reviews
            review_prompt = f"개발자가 수정한 코드입니다:\n\n{previous_submission}\n\n다시 검토해주세요."
            final_review = self.manager.chat(
                [Message(role="user", content=review_prompt)],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._track_usage(review_prompt + final_review, self.manager)
            self._add_turn("manager", final_review, current_phase)

            if self._check_approval(final_review):
                current_phase = WorkflowPhase.APPROVED
                stopped_reason = "approved"
                break

            # Developer revises again
            dev_revise = f"PM의 추가 피드백:\n\n{final_review}\n\n이전 제출물:\n{previous_submission}\n\n다시 수정해주세요."
            developer_response = self.developer.chat(
                [Message(role="user", content=dev_revise)],
                system_prompt=DEVELOPER_SYSTEM_PROMPT,
            )
            self._track_usage(dev_revise + developer_response, self.developer)
            self._add_turn("developer", developer_response, current_phase)

            # Check progress
            if not self._check_progress(developer_response):
                stopped_reason = "no_progress"
                self.console.print(f"\n[yellow]⚠ No meaningful progress for {self.max_no_progress} iterations.[/yellow]")
                break

            previous_submission = developer_response

        if not stopped_reason:
            stopped_reason = "max_iterations"

        self.console.print(f"\n[bold]Final Statistics:[/bold]")
        self.console.print(f"  Iterations: {iterations} | Tokens: {self.total_tokens:,} | Cost: ${self.total_cost:.4f} | Reason: {stopped_reason}")

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_submission,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
            total_tokens=self.total_tokens,
            total_cost=self.total_cost,
            stopped_reason=stopped_reason,
        )

    def run_planning(self, project_description: str) -> WorkflowResult:
        """Run a project planning workflow"""
        self.conversation_history = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.no_progress_count = 0
        self.previous_submission_text = None
        current_phase = WorkflowPhase.PLANNING
        stopped_reason = ""

        self._display_message("system", f"Starting project planning (Mode: {self.budget_mode})...\n\n**Project:**\n{project_description}", "start")

        iterations = 0
        previous_plan = ""

        while iterations < self.max_iterations:
            iterations += 1
            self._display_budget_status()

            # Check budget limits
            exceeded, reason = self._check_budget_limits()
            if exceeded:
                stopped_reason = reason
                self.console.print(f"\n[red]⚠ Budget limit exceeded: {reason}[/red]")
                break

            # User checkpoint
            if not self._user_checkpoint(iterations):
                stopped_reason = "user_stopped"
                break

            # Developer creates/revises plan
            if iterations == 1:
                plan_prompt = DEVELOPER_PLAN_PROMPT.format(requirements=project_description)
            else:
                plan_prompt = f"PM 피드백을 반영하여 계획을 수정해주세요:\n\n피드백:\n{manager_feedback}\n\n이전 계획:\n{previous_plan}"

            developer_plan = self.developer.chat(
                [Message(role="user", content=plan_prompt)],
                system_prompt=DEVELOPER_SYSTEM_PROMPT,
            )
            self._track_usage(plan_prompt + developer_plan, self.developer)
            self._add_turn("developer", developer_plan, current_phase)

            # Check progress
            if not self._check_progress(developer_plan):
                stopped_reason = "no_progress"
                self.console.print(f"\n[yellow]⚠ No meaningful progress for {self.max_no_progress} iterations.[/yellow]")
                break

            previous_plan = developer_plan

            # Manager reviews plan
            review_prompt = MANAGER_PLANNING_PROMPT.format(
                requirements=project_description, plan=developer_plan
            )
            manager_feedback = self.manager.chat(
                [Message(role="user", content=review_prompt)],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._track_usage(review_prompt + manager_feedback, self.manager)
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                stopped_reason = "approved"
                break

        if not stopped_reason:
            stopped_reason = "max_iterations"

        self.console.print(f"\n[bold]Final Statistics:[/bold]")
        self.console.print(f"  Iterations: {iterations} | Tokens: {self.total_tokens:,} | Cost: ${self.total_cost:.4f} | Reason: {stopped_reason}")

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_plan,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
            total_tokens=self.total_tokens,
            total_cost=self.total_cost,
            stopped_reason=stopped_reason,
        )

    def run_documentation(self, topic: str, context: str = "") -> WorkflowResult:
        """Run a documentation workflow"""
        self.conversation_history = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.no_progress_count = 0
        self.previous_submission_text = None
        current_phase = WorkflowPhase.IMPLEMENTATION
        stopped_reason = ""

        doc_request = f"다음 주제에 대한 문서를 작성해주세요: {topic}"
        if context:
            doc_request += f"\n\n참고 컨텍스트:\n{context}"

        self._display_message("system", f"Starting documentation (Mode: {self.budget_mode})...\n\n**Topic:**\n{topic}", "start")

        iterations = 0
        previous_doc = ""

        while iterations < self.max_iterations:
            iterations += 1
            self._display_budget_status()

            # Check budget limits
            exceeded, reason = self._check_budget_limits()
            if exceeded:
                stopped_reason = reason
                self.console.print(f"\n[red]⚠ Budget limit exceeded: {reason}[/red]")
                break

            # User checkpoint
            if not self._user_checkpoint(iterations):
                stopped_reason = "user_stopped"
                break

            # Developer writes/revises doc
            if iterations == 1:
                developer_doc = self.developer.chat(
                    [Message(role="user", content=doc_request)],
                    system_prompt=DEVELOPER_SYSTEM_PROMPT + "\n\n문서 작성 시 명확하고 구조화된 형식을 사용하세요.",
                )
                self._track_usage(doc_request + developer_doc, self.developer)
            else:
                doc_revise = f"PM 피드백을 반영하여 문서를 수정해주세요:\n\n피드백:\n{manager_feedback}\n\n이전 문서:\n{previous_doc}"
                developer_doc = self.developer.chat(
                    [Message(role="user", content=doc_revise)],
                    system_prompt=DEVELOPER_SYSTEM_PROMPT,
                )
                self._track_usage(doc_revise + developer_doc, self.developer)

            self._add_turn("developer", developer_doc, current_phase)

            # Check progress
            if not self._check_progress(developer_doc):
                stopped_reason = "no_progress"
                self.console.print(f"\n[yellow]⚠ No meaningful progress for {self.max_no_progress} iterations.[/yellow]")
                break

            previous_doc = developer_doc

            # Manager reviews
            current_phase = WorkflowPhase.REVIEW
            review_prompt = f"다음 문서를 검토해주세요:\n\n주제: {topic}\n\n문서:\n{developer_doc}"
            manager_feedback = self.manager.chat(
                [Message(role="user", content=review_prompt)],
                system_prompt=MANAGER_SYSTEM_PROMPT,
            )
            self._track_usage(review_prompt + manager_feedback, self.manager)
            self._add_turn("manager", manager_feedback, current_phase)

            if self._check_approval(manager_feedback):
                current_phase = WorkflowPhase.APPROVED
                stopped_reason = "approved"
                break

            current_phase = WorkflowPhase.IMPLEMENTATION

        if not stopped_reason:
            stopped_reason = "max_iterations"

        self.console.print(f"\n[bold]Final Statistics:[/bold]")
        self.console.print(f"  Iterations: {iterations} | Tokens: {self.total_tokens:,} | Cost: ${self.total_cost:.4f} | Reason: {stopped_reason}")

        return WorkflowResult(
            success=current_phase == WorkflowPhase.APPROVED,
            final_output=previous_doc,
            conversation_history=self.conversation_history,
            iterations=iterations,
            phase=current_phase,
            total_tokens=self.total_tokens,
            total_cost=self.total_cost,
            stopped_reason=stopped_reason,
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
