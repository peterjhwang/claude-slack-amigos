## Summary
<!-- 1–3 bullet points on what this PR does -->

## Related issue
Closes #

## Type of change
- [ ] Bug fix
- [ ] New feature / agent capability
- [ ] Refactor (no behaviour change)
- [ ] Docs / README
- [ ] CI / tooling

## Testing
<!-- How did you test this? Did you run it against a real Slack workspace? -->
- [ ] Syntax check passes (`python -c "import ast; [ast.parse(open(f).read()) for f in __import__('pathlib').Path('.').rglob('*.py')]"`)
- [ ] Ran locally against a test Slack workspace
- [ ] Tested the affected agent end-to-end

## Checklist
- [ ] No secrets or API keys in the code
- [ ] `.env.example` updated if new env vars were added
- [ ] `README.md` updated if setup steps changed
- [ ] No `print()` statements in production paths (use `logging`)
