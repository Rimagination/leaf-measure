# Release Checklist

Use this checklist before making `leaf-measure` public.

## Already Decided

- release path: Option B
- repository-authored code and docs license: MIT

## Repository Identity

- choose the real repository URL
- replace `<repo-url>` in `README.md`
- confirm repository title and description

## License

- keep `LICENSE.md` aligned with `README.md`, `pyproject.toml`, and `docs/licensing.md`
- confirm the public repository only contains repository-authored materials plus lightweight notices

## Upstream Assets

- keep `macros/original/`, `fixtures/`, and `golden/` externalized from the public repo
- keep runtime staging/bootstrap flow working
- keep explicit source and provenance notes for external assets

## README

- keep the agent-first usage examples
- verify installation instructions still match reality
- add the real repository URL

## Verification

- run the full test suite
- repeat one clean cold-start setup
- confirm the main example command still works

## Packaging

- confirm `pip install -e .[dev]` works in a clean directory
- confirm `bootstrap.ps1` still provides useful next-step guidance

## Messaging

- prepare one canonical prompt for agent users
- prepare one canonical manual CLI example
- prepare one short summary for public announcement or documentation
