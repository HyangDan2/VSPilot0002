# Git Commit Guide

## Commit Message Format

This project follows the **Conventional Commits** specification for clear and consistent commit messages.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc.)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files

### Scope (Optional)

The scope should be the name of the affected module/component:

- **gui**: GUI-related changes
- **serial**: Serial communication changes
- **main**: Main application changes
- **config**: Configuration changes
- **deps**: Dependencies changes

### Subject

- Use the imperative mood ("Add" not "Added")
- Don't capitalize the first letter
- No period at the end
- Maximum 50 characters

### Body (Optional)

- Use the imperative mood
- Include motivation for the change
- Contrast with previous behavior
- Wrap at 72 characters

### Footer (Optional)

- Reference issues and pull requests
- Note breaking changes

## Examples

### Good Examples

```
feat(gui): add serial port scanning functionality

Added automatic scanning of available serial ports every 5 seconds
with visual feedback in the scan button.

Closes #123
```

```
fix(serial): resolve connection timeout issue

Fixed timeout handling in SerialWorker to prevent hanging
when device doesn't respond.

Fixes #456
```

```
refactor: split monolithic file into modular structure

- Separated SerialWorker into serial/worker.py
- Moved GUI components to gui/ directory
- Created proper module structure with __init__.py files

Breaking change: Import paths have changed
```

```
docs: update README with installation instructions

Added detailed setup instructions and usage examples.
```

```
style(gui): improve code formatting consistency

Applied consistent spacing and imports organization
across all GUI modules.
```

### Bad Examples

```
❌ Fixed bug
❌ Added new feature
❌ Updated files
❌ WIP
❌ asdf
❌ Fixed the thing that was broken
```

## Branch Naming

### Feature Branches
- `feature/port-scanning`
- `feature/gui-improvements`
- `feature/add-logging`

### Bug Fix Branches
- `fix/connection-timeout`
- `fix/ui-layout-issue`
- `fix/serial-port-detection`

### Release Branches
- `release/v1.0.0`
- `release/v1.1.0`

### Hotfix Branches
- `hotfix/critical-connection-bug`
- `hotfix/memory-leak-fix`

## Workflow

1. **Create feature branch** from `main`:
   ```bash
   git checkout -b feature/new-functionality
   ```

2. **Make commits** following the convention:
   ```bash
   git commit -m "feat(gui): add new serial port configuration panel"
   ```

3. **Push branch** and create Pull Request:
   ```bash
   git push origin feature/new-functionality
   ```

4. **Merge** after review (use squash merge for feature branches)

5. **Delete** merged branch:
   ```bash
   git branch -d feature/new-functionality
   ```

## Additional Tips

### Commit Frequency
- Commit early and often
- Each commit should represent a logical unit of work
- Don't commit broken code to main branch

### Pre-commit Checklist
- [ ] Code runs without errors
- [ ] All tests pass
- [ ] Code follows project style guide
- [ ] Commit message follows convention
- [ ] No debugging code left in

### Commit Message Tools
Consider using tools like:
- `commitizen` - Interactive commit message generator
- `conventional-changelog` - Generate changelog from commits
- Git hooks for commit message validation

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)