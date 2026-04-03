# Licensing And Source Notes

## Upstream Method Assets

The FAMeLeS paper states that the script, trial pictures, and user guide are available on Figshare:

- DOI: `10.6084/m9.figshare.22354405`

The paper text in this workspace indicates that the article itself is distributed under a Creative Commons Attribution-NonCommercial-NoDerivs license. Before any external redistribution or automation around the method assets, verify the exact license terms attached to the Figshare package itself.

## Repository Policy

This repository now follows Option B:

- upstream macro files and reference data are expected to live in an external assets directory
- repository-authored code, scripts, docs, and skill definitions in this repository are released under the MIT License
- the project code in this repository may patch macro text at runtime, but should do so only on temporary copies written into a run workspace
- upstream macro files should not be edited in place in version control

## Practical Constraint

If the Figshare package license or update policy changes, adjust the external staging/bootstrap flow so that the resolved upstream source and version remain explicit in run metadata.
