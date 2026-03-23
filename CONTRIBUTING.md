# Contributing to EvoForge

Thank you for your interest in contributing to EvoForge! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub:

1. Check if the issue already exists
2. Provide a clear description with steps to reproduce (for bugs)
3. Include relevant logs, screenshots, or system information

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes following our style guidelines
4. Add tests if applicable
5. Commit your changes (`git commit -am 'Add my feature'`)
6. Push to your branch (`git push origin feature/my-feature`)
7. Open a Pull Request with a clear description

### Pull Request Process

- Ensure all tests pass
- Update documentation if needed
- Pull requests will be reviewed by maintainers
- Address any requested changes
- Once approved, PRs will be merged by maintainers

## Development Setup

```bash
# Clone the repository
git clone https://github.com/johnnykang101/evoforge.git
cd evoforge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Run tests
pytest
```

## Project Structure

```
evoforge/
├── evoforge/          # Core package
│   ├── core/          # Main evolution engine and orchestration
│   ├── genome/        # Architecture genome representation and schema
│   ├── variation/     # Mutation and crossover operators
│   ├── fitness/       # Multi-objective fitness evaluation
│   ├── sandbox/       # A/B testing and isolated execution
│   ├── knowledge/     # Convergent Knowledge Synthesis Engine
│   ├── skills/        # Skill Crystallization Cache with validation
│   └── utils/         # Configuration, logging, and helpers
├── docs/              # Documentation
├── tests/             # Test suite
├── examples/          # Usage examples
└── results/           # Benchmark results and graphs
```

## Coding Standards

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for public APIs (Google style)
- Keep functions focused and modular
- Add unit tests for new functionality

## Commit Guidelines

We follow semantic commit messages:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `style:` formatting, no code changes
- `refactor:` code restructuring
- `test:` adding or updating tests
- `chore:` maintenance tasks

Example: `feat(mec): add genome crossover operator`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Questions?** Feel free to reach out via GitHub issues or discussions.
