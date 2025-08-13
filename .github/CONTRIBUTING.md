# Contributing to Video Scraper Service

Thank you for your interest in contributing! 🎉

## Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/yourusername/tiktok-video-scrapper.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Make changes** and test locally
5. **Submit a Pull Request**

## Development Setup

### Prerequisites
- Python 3.9+ 
- Git

### Setup Steps
```bash
# Clone your fork
git clone https://github.com/yourusername/tiktok-video-scrapper.git
cd tiktok-video-scrapper

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys (optional for basic testing)

# Run tests
python -m pytest tests/ -v

# Test the app
python -c "from app.main import app; print('✅ Ready to go!')"
```

## Pull Request Guidelines

### Before Submitting
- ✅ One feature/fix per PR
- ✅ Write clear, descriptive commit messages
- ✅ Include tests for new functionality  
- ✅ Update documentation if needed
- ✅ Follow existing code style
- ✅ Make sure tests pass locally

### PR Description Template
```markdown
## What does this PR do?
Brief description of changes

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Other: ___________

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Tested manually (if applicable)

## Notes
Any additional context or considerations
```

## Code Review Process

1. **Automated checks** must pass ✅
   - Tests (Python 3.9, 3.10, 3.11)
   - Linting
   - Docker build
2. **At least 1 maintainer review** required
3. **Address any requested changes**
4. **Maintainer will merge** when approved

## Code Style

- Follow existing patterns in the codebase
- Use meaningful variable and function names
- Add docstrings for new functions/classes
- Keep functions focused and concise
- Use type hints where helpful

## Testing

- Write tests for new features
- Test both success and error cases
- Use descriptive test names
- Mock external services (OpenAI, yt-dlp)

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/unit/test_cache.py -v

# With coverage
pip install pytest-cov
python -m pytest tests/ --cov=app --cov-report=html
```

## Reporting Issues

### Bug Reports
- Use the bug report template
- Include steps to reproduce
- Provide environment details
- Include error messages if any

### Feature Requests
- Describe the problem you're trying to solve
- Explain your proposed solution
- Consider backwards compatibility

## Getting Help

- **Questions?** Open a GitHub discussion
- **Stuck on something?** Comment on your PR
- **Need guidance?** Open an issue with the `question` label

## Recognition

All contributors will be recognized in our README and releases! 🌟

## Code of Conduct

Please be respectful and inclusive. We want this to be a welcoming community for everyone.

---

Happy contributing! 🚀