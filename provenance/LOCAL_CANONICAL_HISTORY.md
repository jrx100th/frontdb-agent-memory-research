# Local Canonical History Provenance

The initial research state originated in a local Git repository.

Original local commits:

```text
61a250890552d61ebcdcb0633b15106a50922edd
[IMPL] initialize shared research coordination repository

03092e52eed9bf3ba0ead16979a9469d0031c55e
[IMPL] add frozen v0 architecture and experiment state

16ce2463a98bb6ab514504b2422b93e58809510d
[IMPL] import staged memory implementation and deterministic tests

d6e0b328b7b62902bd61a3777932616fa2045b24
[IMPL] publish staging test evidence and orchestrator handoff
```

LOCAL_CANONICAL_HEAD:
`d6e0b328b7b62902bd61a3777932616fa2045b24`

REMOTE IMPORT NOTE:
Native Git transport from the implementation environment was unavailable.
The clean working-tree snapshot was imported through the authenticated
GitHub connector/API. Therefore remote bootstrap commit SHAs differ from
the original local Git commit SHAs.

The local SHAs remain provenance identifiers, not remote commit IDs.

The pre-import tracked snapshot contained 36 files. Its file-level SHA-256 manifest is `provenance/SNAPSHOT_SHA256SUMS.txt`; the manifest file itself had SHA-256 `aa55a9801549553815ec3b8cd75a40439717b3d261f9ac29df8b79346bce7c92` before it was added to the remote repository.
