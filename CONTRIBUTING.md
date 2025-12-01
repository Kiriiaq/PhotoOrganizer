# 🤝 Contributing to PhotoOrganizer

Thank you for considering contributing to PhotoOrganizer! This document provides guidelines and information for contributors.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

---

## 📜 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Prioritize the project's goals

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing others' private information
- Other unprofessional conduct

---

## 📞 Contact

- **Developer:** Kiriiaq
- **Email:** manugrolleau48@gmail.com
- **Ko-fi:** https://ko-fi.com/kiriiaq
- **GitHub:** https://github.com/Kiriiaq/PhotoOrganizer

---

## 🚀 How to Contribute

### 1. Fork the Repository

```bash
# Click "Fork" on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/PhotoOrganizer.git
cd PhotoOrganizer
```

### 2. Create a Branch

```bash
# Create a new branch for your feature or bugfix
git checkout -b feature/amazing-feature
# or
git checkout -b bugfix/issue-123
```

### 3. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add comments for complex logic
- Update documentation if needed

### 4. Test Your Changes

```bash
# Run the application
python main.py

# Test all features:
# - File analysis
# - File organization
# - Cancel operation
# - UI responsiveness
```

### 5. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "Add feature: intelligent duplicate detection"
```

### 6. Push to Your Fork

```bash
git push origin feature/amazing-feature
```

### 7. Open a Pull Request

- Go to the original repository on GitHub
- Click "New Pull Request"
- Select your branch
- Fill in the PR template with details

---

## 💻 Development Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/PhotoOrganizer.git
cd PhotoOrganizer

# Install dependencies
pip install customtkinter exifread piexif Pillow darkdetect

# Run the application
python main.py
```

### Optional: Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 📝 Code Style Guidelines

### Python Style (PEP 8)

- **Indentation:** 4 spaces (no tabs)
- **Line length:** Max 100 characters
- **Naming conventions:**
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Documentation

```python
def analyze_files(source_dir, file_types, recursive=True):
    """
    Analyze files in a directory and extract metadata.

    Args:
        source_dir (str): Path to the source directory
        file_types (list): List of file extensions to analyze
        recursive (bool): Whether to search subdirectories

    Returns:
        dict: Dictionary containing analysis results
    """
    # Implementation here
    pass
```

### Code Organization

```
PhotoOrganizerV5/
├── core/              # Core business logic
│   ├── file_operations.py
│   └── metadata.py
├── gui/               # User interface
│   ├── app.py
│   └── frames/
├── utils/             # Utility functions
│   ├── progress_utils.py
│   └── ui_utils.py
└── main.py           # Entry point
```

### Import Order

```python
# 1. Standard library imports
import os
import sys
from datetime import datetime

# 2. Third-party imports
import customtkinter as ctk
import exifread
from PIL import Image

# 3. Local imports
from core.metadata import extract_metadata
from utils.file_utils import get_file_extension
```

---

## 📤 Submitting Changes

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guidelines
- [ ] All new functions have docstrings
- [ ] No unnecessary print statements (use logging)
- [ ] No hardcoded file paths
- [ ] UI changes are tested on Windows
- [ ] Documentation is updated (README.md if needed)
- [ ] Commit messages are clear and descriptive

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement

## Testing
Describe how you tested your changes

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Fixes #123
```

---

## 🐛 Reporting Bugs

### Before Reporting

1. Check if the bug has already been reported
2. Try to reproduce the bug
3. Gather relevant information

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g. Windows 11]
- Python version: [e.g. 3.11.9]
- PhotoManager version: [e.g. 5.0]

**Additional context**
Any other information about the problem.
```

---

## 💡 Feature Requests

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context or screenshots.
```

### Feature Ideas

We welcome feature suggestions! Some areas of interest:

- **Export/Import:** CSV/JSON export of analysis results
- **Duplicate Detection:** Find and manage duplicate photos
- **Batch Renaming:** Rename files based on metadata
- **Geocoding:** Convert GPS coordinates to location names
- **Performance:** Speed optimizations for large collections
- **Localization:** Multi-language support
- **Cross-platform:** macOS and Linux support

---

## 🔍 Code Review Process

### What We Look For

1. **Functionality:** Does it work as intended?
2. **Code Quality:** Is it clean and maintainable?
3. **Performance:** Does it perform well?
4. **Documentation:** Is it well-documented?
5. **Testing:** Has it been tested?

### Review Timeline

- Small fixes: 1-3 days
- New features: 3-7 days
- Large changes: 7-14 days

We appreciate your patience!

---

## 🏆 Recognition

Contributors will be:

- Listed in the project's contributors list
- Mentioned in release notes for significant contributions
- Given credit in the README.md

---

## 📞 Questions?

- **GitHub Issues:** For bugs and features
- **GitHub Discussions:** For questions and ideas
- **Email:** contact@photomanager.pro

---

## 📜 License

By contributing to PhotoOrganizer, you agree that your contributions will be licensed under the MIT License with Commons Clause.

---

<div align="center">

**Thank you for contributing to PhotoOrganizer!**

Your help makes this project better for everyone.

Développé par Kiriiaq - [Ko-fi](https://ko-fi.com/kiriiaq) | [Email](mailto:manugrolleau48@gmail.com)

</div>
