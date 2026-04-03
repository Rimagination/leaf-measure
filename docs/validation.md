# Validation Strategy

Validation is an internal trust layer, not the main user interface.

The repository keeps:

- bundled trial input data
- golden outputs
- automated regression tests

Validation has two roles:

1. prove that the implementation reproduces known-good reference outputs
2. catch unintended behavior drift when the execution layer changes

Normal users should mainly see run outputs, trait explanations, and any warnings relevant to their dataset. They do not need raw regression logs by default.

