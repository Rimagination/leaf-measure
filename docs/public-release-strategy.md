# Public Release Strategy

Adopted release path: **Option B**
Selected repository license for repository-authored materials: **MIT**

This document answers the release-shaping question for publishing `leaf-measure` as a public repository:

How should the repository handle its own code license while also depending on upstream FAMeLeS assets and validation data that are no longer bundled into the public repo?

## The Two Real Options

### Option A: Keep Bundled Upstream Assets

Under this model, the repository continues to ship:

- `macros/original/`
- `fixtures/`
- `golden/`

Repository-authored code and docs would get their own license, while upstream assets would remain covered by separate provenance and notice files.

#### Advantages

- easiest for users to clone and run immediately
- simplest validation story because fixtures and golden outputs stay in-repo
- strongest demo experience for local testing

#### Risks

- license clarity is weaker
- public readers may wrongly assume the whole repository is covered by one permissive license
- every release must keep upstream provenance and redistribution assumptions accurate

#### What This Requires

1. add a license for repository-authored code and docs only
2. add explicit notices for upstream assets
3. make it very clear in `README.md` and `LICENSE.md` that not all repository contents share the same license

### Option B: Stop Bundling Upstream Assets

Under this model, the repository would:

- keep only repository-authored code, docs, and lightweight metadata
- fetch FAMeLeS assets from the official upstream source at runtime or setup time
- avoid shipping upstream fixtures and golden files directly

#### Advantages

- cleanest public-license story
- easiest to publish under a standard open-source license
- lowest long-term legal ambiguity

#### Risks

- setup becomes less immediate
- validation becomes harder unless a separate private or optional test-data path is kept
- demo experience is slightly worse unless bootstrap automation is very good

#### What This Requires

1. implement a bootstrap or fetch flow for upstream assets
2. move validation to an optional path or a separate data package
3. publish a single license for repository-authored code and docs

## Adopted Path

Use a standard open-source license for repository-authored code and documentation, and stop bundling upstream FAMeLeS assets directly in the public repository.

Why this is the better long-term choice:

- the public licensing story becomes much clearer
- the repository is easier to explain, reuse, and redistribute
- future maintenance is safer because upstream asset terms are less likely to be misrepresented

This is the more professional release path even if it costs a bit more setup work.

## Transitional Path

If you want to publish quickly before implementing runtime fetches, use this temporary path:

1. publish with repository-authored code and docs clearly separated from upstream assets
2. keep explicit warnings in `README.md` and `LICENSE.md`
3. treat that state as temporary
4. plan a follow-up release that migrates to Option B

## Recommended License Split

If you choose Option B:

- repository-authored code: MIT or Apache-2.0
- repository-authored docs: same as repository code, unless you want a documentation-specific license
- upstream FAMeLeS assets: not bundled; referenced by source DOI and fetched separately

If you choose Option A:

- repository-authored code and docs: MIT or Apache-2.0
- upstream FAMeLeS assets: separate notices, separate provenance, no implication that they inherit the repository license

## Practical Next Steps

With the adopted path, the practical tasks are:

1. keep the MIT license in sync with packaging metadata and README text
2. keep upstream assets externalized from the public package
3. maintain a bootstrap or staging path that verifies upstream assets
4. keep validation able to run against optional external data
