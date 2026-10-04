# Investigate Bug Skill

Investigate a bug by following evidence-first methodology.

## Requirements
- code.search
- fs.read
- shell.execute
- test.run
- git.diff

## Workflow
1. Reproduce the failure by running tests
2. Inspect error output and stack traces
3. Search for relevant code symbols
4. Read implicated files
5. Form a hypothesis about root cause
6. Propose a minimal patch
7. Run targeted tests to verify
8. Run full test suite to check for regressions

## Success Criteria
- Tests pass
- No new warnings introduced
- Diff is minimal and focused
