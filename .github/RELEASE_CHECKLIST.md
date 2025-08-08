# Release Checklist

Use this checklist when preparing a manual release.

## Pre-Release Checks

### Code Quality
- [ ] All tests pass locally (`uv run pytest src/tests/`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Formatting is consistent (`uv run ruff format --check .`)
- [ ] Type checking passes (`uv run mypy src/`)
- [ ] Pre-commit hooks pass (`uv run pre-commit run --all-files`)

### Documentation
- [ ] README.md is up to date
- [ ] CHANGELOG.md has unreleased changes documented
- [ ] API documentation is current
- [ ] Version-specific documentation is ready

### Dependencies
- [ ] Dependencies are up to date (`uv sync`)
- [ ] Security vulnerabilities checked (`uv run safety check`)
- [ ] License compliance verified

### Environment Testing
- [ ] Docker build succeeds (`docker compose build`)
- [ ] Docker containers start successfully (`docker compose up -d`)
- [ ] Health checks pass (`make health-check`)
- [ ] Integration tests pass

## Release Process

### 1. Version Planning
- [ ] Determine version type (major/minor/patch)
- [ ] Review breaking changes (if major version)
- [ ] Plan migration path (if needed)

### 2. Version Bump
Choose one method:

**Automatic (recommended):**
```bash
make bump-patch    # or bump-minor, bump-major
```

**Manual:**
- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md with new version
- [ ] Commit changes: `git commit -m "Bump version to X.Y.Z"`
- [ ] Create tag: `git tag -a "vX.Y.Z" -m "Release X.Y.Z"`
- [ ] Push: `git push && git push --tags`

### 3. GitHub Release
The release workflow will automatically:
- [ ] Run complete test suite
- [ ] Build Python packages
- [ ] Build and push Docker images
- [ ] Create GitHub release with notes
- [ ] Publish to container registry

### 4. Post-Release Verification
- [ ] GitHub release created successfully
- [ ] Docker images available (`ghcr.io/owner/repo:version`)
- [ ] Release notes are accurate
- [ ] Download links work
- [ ] Documentation updated (if needed)

### 5. Communication
- [ ] Announce on relevant channels
- [ ] Update any dependent projects
- [ ] Close related issues/milestones

## Hotfix Releases

For urgent fixes to production:

1. **Create hotfix branch** from latest release tag:
   ```bash
   git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z
   ```

2. **Apply minimal fix** and test thoroughly

3. **Follow release process** with patch version bump

4. **Merge back** to main branch:
   ```bash
   git checkout main
   git merge hotfix/vX.Y.Z+1
   ```

## Rollback Procedure

If a release has critical issues:

1. **Immediate action:**
   - Mark GitHub release as pre-release
   - Update Docker tags to point to previous version

2. **Create hotfix** following procedure above

3. **Communicate** the rollback and timeline for fix

## Version Naming Conventions

- **Stable releases**: `vX.Y.Z` (e.g., v1.2.3)
- **Pre-releases**: `vX.Y.Z-alpha.N`, `vX.Y.Z-beta.N`, `vX.Y.Z-rc.N`
- **Development**: Use pre-release versions

## Automation

This project supports automated releases via conventional commits:

- `feat: description` → Minor release
- `fix: description` → Patch release
- `feat!: description` → Major release
- `BREAKING CHANGE: description` → Major release

**Enable automated releases** by merging commits with conventional format to main branch.
