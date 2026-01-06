# AI Collab - Agile AI Collaboration Tool

PM(OpenAI GPT-5.1 Codex Mini)과 Developer(Claude Sonnet 4)가 애자일 방식으로 협업하는 CLI 도구입니다.

> 깐깐한 PM이 승인할 때까지 개발자가 계속 수정하는 방식으로 높은 품질의 결과물을 생성합니다.

## Features

- **코드 개발**: 요구사항 → 계획 → 구현 → 리뷰 → 승인
- **코드 리뷰**: 기존 코드 검토 및 개선
- **프로젝트 기획**: 구현 계획 수립 및 검토
- **문서 작성**: 기술 문서 작성 및 품질 검토

## Installation

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ai-collab.git
cd ai-collab

# Setup
./setup.sh

# Or manual install
pip install -r requirements.txt
```

## Configuration

### API Keys

```bash
export OPENAI_API_KEY='your-openai-api-key'
export ANTHROPIC_API_KEY='your-anthropic-api-key'
```

### config.yaml (Optional)

```yaml
models:
  manager:
    provider: "openai"
    model: "gpt-5.1-codex-mini"  # Options: "gpt-5.1-codex-mini", "gpt-4o", "o1-mini"
    temperature: 0.3
  developer:
    provider: "anthropic"  # Switch to "openai" if needed
    model: "claude-sonnet-4-20250514"  # Options: "claude-opus-4-20250514", "claude-sonnet-4-20250514"
    temperature: 0.7

workflow:
  # Basic settings
  max_iterations: 10
  output_dir: "./output"

  # Budget Mode: "economy", "balanced", or "quality"
  budget_mode: "balanced"

  # Advanced Cost Control (optional)
  # max_tokens: 50000
  # max_cost: 2.0
  # checkpoint_interval: 5

  # Smart Termination
  max_no_progress: 3
  early_stop_similarity: 0.95
```

#### Switching Providers

To switch the developer to OpenAI:
1. Change `provider: "anthropic"` to `provider: "openai"`
2. Change model to an OpenAI model (e.g., `"gpt-5.1-codex-mini"`, `"gpt-4o"`)

## Advanced Features

### 🎯 Budget Control

AI Collab now includes comprehensive budget control features to prevent API cost overruns:

#### Budget Modes

Choose from three preset budget modes:

| Mode | Max Iterations | Max Tokens | Max Cost | Checkpoint Interval |
|------|---------------|------------|----------|-------------------|
| **economy** | 5 | 30,000 | $1.00 | Every 3 iterations |
| **balanced** | 10 | 50,000 | $2.00 | Every 5 iterations |
| **quality** | 15 | 100,000 | $5.00 | Every 7 iterations |

**Usage:**
```yaml
workflow:
  budget_mode: "economy"  # or "balanced" or "quality"
```

Or via Python:
```python
workflow = CollaborationWorkflow(
    manager_client=manager,
    developer_client=developer,
    budget_mode="economy"
)
```

#### Custom Budget Limits

Override budget mode with custom limits:

```yaml
workflow:
  budget_mode: "balanced"  # Base preset
  max_tokens: 40000        # Custom token limit
  max_cost: 1.5            # Custom cost limit ($)
  checkpoint_interval: 4    # Ask user every 4 iterations
```

**What happens when limits are exceeded:**
- **max_tokens**: Workflow stops automatically, saves progress
- **max_cost**: Workflow stops automatically, saves progress
- **checkpoint_interval**: User is prompted to continue or stop

### 🔄 Smart Early Termination

Automatically detect and stop unproductive iterations:

#### No Progress Detection

Stops workflow if developer makes no meaningful progress for N consecutive iterations:

```yaml
workflow:
  max_no_progress: 3  # Stop after 3 iterations with no progress
```

#### Similarity-Based Stopping

Stops if consecutive submissions are too similar (developer is stuck):

```yaml
workflow:
  early_stop_similarity: 0.95  # Stop if 95%+ similar
```

**Example:**
```
Iteration 1: Developer writes 500 lines of code
Iteration 2: Developer makes minor changes (5 lines)
Iteration 3: Developer makes minor changes (3 lines)
→ Stopped: No meaningful progress for 3 iterations
```

### 📊 Real-Time Monitoring

During execution, you'll see:

```
Budget: 12,450/50,000 tokens (24.9%) | $0.0374/$2.00 (1.9%)

━━━ Checkpoint at iteration 5 ━━━
Tokens used: 25,340 / 50,000
Estimated cost: $0.0760 / $2.00

Continue workflow? [Y/n]:
```

### 📈 Final Statistics

After workflow completion:

```
Final Statistics:
  Iterations: 7
  Total tokens: 31,245
  Estimated cost: $0.0937
  Stop reason: approved
```

**Stop Reasons:**
- `approved` - PM approved the work ✅
- `max_iterations` - Reached iteration limit
- `max_tokens` - Exceeded token budget
- `max_cost` - Exceeded cost budget
- `no_progress` - No meaningful progress detected
- `user_stopped` - User stopped at checkpoint

## Usage

### CLI Commands

```bash
# Development workflow
python cli.py develop "Create a REST API for user authentication"

# Code review
python cli.py review -f your_code.py

# Project planning
python cli.py plan "Build an e-commerce platform"

# Documentation
python cli.py docs "API authentication guide"

# Interactive mode
python cli.py interactive
```

### As a Library

```python
from ai_collab import create_client, CollaborationWorkflow

# Create clients
manager = create_client(provider="openai", model="gpt-5.1-codex-mini")
developer = create_client(provider="anthropic", model="claude-sonnet-4-20250514")

# Basic workflow
workflow = CollaborationWorkflow(
    manager_client=manager,
    developer_client=developer,
    max_iterations=5,
)

# Run
result = workflow.run_development("Create a function to validate emails")
print(f"Approved: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Total tokens: {result.total_tokens}")
print(f"Cost: ${result.total_cost:.4f}")
print(f"Stop reason: {result.stopped_reason}")
print(f"Output: {result.final_output}")
```

#### Advanced Usage with Budget Control

```python
# Economy mode - fast and cheap
workflow_economy = CollaborationWorkflow(
    manager_client=manager,
    developer_client=developer,
    budget_mode="economy",
)

# Custom budget limits
workflow_custom = CollaborationWorkflow(
    manager_client=manager,
    developer_client=developer,
    budget_mode="balanced",      # Start with balanced preset
    max_tokens=30000,            # But limit to 30k tokens
    max_cost=1.0,                # And $1 max cost
    checkpoint_interval=3,        # Ask user every 3 iterations
    max_no_progress=2,           # Stop after 2 iterations with no progress
    early_stop_similarity=0.90,  # Stop if 90%+ similar
)

result = workflow_custom.run_development("Build a REST API")

# Check why it stopped
if result.stopped_reason == "max_cost":
    print("Stopped due to budget limit")
elif result.stopped_reason == "no_progress":
    print("Stopped due to lack of progress")
elif result.stopped_reason == "approved":
    print("Successfully completed!")
```

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Developer (Claude)                                      │
│  - Analyzes requirements                                 │
│  - Creates implementation plan                           │
│  - Writes code                                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  PM/Manager (GPT-5.1 Codex Mini)                         │
│  - Strict code review                                    │
│  - Checks requirements coverage                          │
│  - Identifies bugs, security issues                      │
│  - Provides detailed feedback                            │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
      [NOT APPROVED]              [APPROVED]
              │                         │
              │                         ▼
              │                 ┌───────────────┐
              │                 │ Final Output  │
              │                 └───────────────┘
              │
              ▼
      ┌───────────────┐
      │ Developer     │
      │ Revises Code  │◄────────────┐
      └───────────────┘             │
              │                     │
              ▼                     │
      ┌───────────────┐             │
      │ PM Reviews    │─────────────┘
      │ Again         │   (until approved or max iterations)
      └───────────────┘
```

## Output

Results are saved to `./output/` with full conversation history:

```
output/
└── result_20240115_143052.md
```

## License

MIT
