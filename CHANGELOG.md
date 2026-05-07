# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-07

### Added

- Initial public release.
- Core: `Council`, `Voter` protocol, `function_voter` adapter.
- Value types: `Vote`, `Decision`.
- Persistence: `MeetingStore` protocol with `NullMeetingStore` and
  `JsonMeetingStore` implementations.
- Threshold rules: integer (absolute) and float ratio (rounded up).
- Veto support: any voter can block approval regardless of count.
- Weighted final score aggregation.
- Defensive voter handling: by default a raising voter is recorded as a
  no-vote with score 0; `strict=True` re-raises.
- Three runnable examples: `domain_valuation`, `code_review`,
  `content_moderation`.
- Test suite covering threshold semantics, veto, weighting, error paths,
  and JSON store rotation.
