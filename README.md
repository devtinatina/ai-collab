# AI Collab - Agile AI Collaboration Tool

PM(OpenAI GPT-4)과 Developer(Claude)가 애자일 방식으로 협업하는 CLI 도구입니다.

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
    model: "gpt-4o"
    temperature: 0.3
  developer:
    provider: "anthropic"
    model: "claude-sonnet-4-20250514"
    temperature: 0.7

workflow:
  max_iterations: 10
  output_dir: "./output"
```

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
manager = create_client(provider="openai", model="gpt-4o")
developer = create_client(provider="anthropic", model="claude-sonnet-4-20250514")

# Create workflow
workflow = CollaborationWorkflow(
    manager_client=manager,
    developer_client=developer,
    max_iterations=5,
)

# Run
result = workflow.run_development("Create a function to validate emails")
print(f"Approved: {result.success}")
print(f"Iterations: {result.iterations}")
print(f"Output: {result.final_output}")
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
│  PM/Manager (GPT-4)                                      │
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
