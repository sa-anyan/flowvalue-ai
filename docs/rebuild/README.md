# Entire-application rebuild starting point

Founder decision: rebuild the entire app, retaining the GitHub checkpoint for selective recovery.

No implementation architecture or first feature has been selected in this branch. Existing canonical product requirements remain in the parent docs directory. Historical phase reports concern the checkpoint application, not delivered functionality in the empty rebuild.

Checkpoint: `checkpoint-before-costing-rebuild-2026-10-29` at commit `a6c0a471ba1669ed10abbceeae80fa3a9006f612`.

Before recovering a feature, identify its minimum files and dependencies, check source licences and source lineage, and agree how it fits the new structure. Restore only the agreed pieces. Do not copy local secrets or blindly migrate old cloud deployment/database settings.

Verification of this reset consists of checking the checkpoint remains available, the new tree contains no active application/runtime files, the local archive is outside Git, and production refs are unchanged. Old application tests cannot run on an intentionally empty source tree; their results remain historical checkpoint evidence.
