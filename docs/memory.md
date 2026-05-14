-------------------
feat_req__persistency__reset_resistant
feat_req__persistency__recovery_from_reset
feat_req__persistency__atomic_store


The above requirements are tested with FIT implementation.
First analyze the difference in FIT and CIT apporach of testing by understanding the implementation in tmp/persistency.
And analyze for the requirements have we creatively covered all scenarios for it.
this comment we got for previous PR.
I would consider scenarios with more kvs instances - does deafult files required for one instance mix into second witch should use it? etc.
Understand his reasoning or apporach for testing requirements for FIT approach and check if our implementation
aligns or covered it.
-------------------

This was said in the context of PR #9 about default values. He was asking about multi-instance isolation as a general principle for testing. The approach is:

For each feature requirement, think about what happens with multiple KVS instances

For reset_resistant: what happens when 2 instances rotate simultaneously?

For recovery_from_reset: what if 2 instances have a reset mid-write, does each recover independently?

For atomic_store: what if 2 instances flush simultaneously, does each write atomically without interfering?

Looking at the reset_resistant requirement specifically, the current tests cover single instance behavior with two flushes and multi-instance scenarios where each rotates independently without cross-contamination, but there's a gap around testing the minimum snapshot count configuration.

When max_count is 1, I need to verify whether the old snapshot gets overwritten atomically or if there's a vulnerable window where neither snapshot exists. The multi-instance case is already covered per the reviewer's feedback, which is the most critical scenario. I'm also missing tests for larger key sets in a single flush and actual rollback verification during system failure, though that last one is difficult to test at the FIT level without process termination.

For recovery_from_reset, the single instance test validates that after a simulated reset without flushing, the disk still holds the last flushed value. The main gap here is testing what happens when two instances both have pending writes and one experiences a reset—I need to verify they each recover to their own last consistent state independently.

I should also add coverage for recovery after multiple successive flushes to confirm it restores to the latest snapshot rather than an older one, and test the edge case of a fresh KVS directory with no existing data. Following the reviewer's pattern of requiring multi-instance tests for each requirement, I'm missing a TestRecoveryFromResetMultiInstance test.

For atomic_store, the current tests cover the happy path with three keys flushing successfully and the no-flush case where no snapshot is created. The missing scenarios involve partial write failures and what happens when atomicity is violated mid-operation. The reviewer's core insight is that integration tests need to verify behavior across multiple KVS instances sharing the same directory—not just single-instance behavior—because the feature requirements are about system-level persistence guarantees. Looking at the three requirements, I can see that reset_resistant has both single and multi-instance coverage, but recovery_from_reset is missing the multi-instance scenario, and atomic_store needs the same treatment to ensure isolation properties hold when instances operate concurrently.

Coverage Analysis per Requirement
feat_req__persistency__reset_resistant
Write operations shall complete successfully, or roll back to the previous state. In case of interruption, rollback to previous consistent state.

Scenario	Coverage	Notes
Single instance: flush → rotate → both snapshots on disk	✅ TestResetResistant	Checks kvs_1_0 (new) and kvs_1_1 (old) both exist with correct values and .hash files
Multi-instance: two instances rotate independently in shared directory	✅ TestResetResistantMultiInstance	Checks all 4 snapshots (kvs_1_0, kvs_1_1, kvs_2_0, kvs_2_1) and cross-contamination
snapshot_max_count=1 (minimum): only current snapshot exists	❌ Missing	With max_count=1 there is no rollback snapshot — does the KVS still behave safely?
Hash file integrity after rotation	✅ test_hash_files_exist	Both .hash files verified
Verdict: Multi-instance scenario is covered (reviewer's concern addressed). One gap: the edge case of snapshot_max_count=1 — the requirement says "roll back to previous state" but there is no previous state when max_count=1.

feat_req__persistency__recovery_from_reset
After a reset, all key-value pairs shall reflect either the last successful write or the previous consistent state.

Scenario	Coverage	Notes
Single instance: flush → set (no flush) → restart → disk has old value	✅ TestRecoveryFromReset	Simulates reset by dropping KVS without flush; verifies kvs_1_0.json = 50.0
Multi-instance: two instances, both have unflushed writes, each recovers independently	❌ Missing	Instance 1 and Instance 2 share directory; both get "reset" (no flush); each should recover to its own last-flushed value without interference
Recovery after 2+ flushes: recovers to most recent, not older snapshot	❌ Missing	After 3 flushes (→ 3 snapshots), simulate reset — KVS should load kvs_1_0.json, not kvs_1_1.json
Fresh start (no existing snapshot): recovery succeeds with empty KVS	❌ Missing	Edge case — restart with no prior snapshot file
Verdict: Only single-instance, single-snapshot recovery is tested. Following the reviewer's multi-instance principle, a TestRecoveryFromResetMultiInstance is missing — two instances in the same directory, each "reset", each should independently recover to its own last flushed state.

feat_req__persistency__atomic_store
Either all key-value pairs are written, or no changes are made at all.

Scenario	Coverage	Notes
Single instance: 3 keys, one flush → all 3 in snapshot	✅ TestAtomicStore	Snapshot inspection + log-based read-back after KVS reload
Single instance no-flush: keys in memory, no snapshot created	✅ TestAtomicStoreNoPartialWrite	Asserts kvs_1_0.json does NOT exist
Multi-instance: two instances flush independently → no cross-write	❌ Missing	Instance 1 flushes keys A,B,C; Instance 2 flushes keys X,Y,Z — each snapshot must contain only its own keys (atomicity + isolation)
Many-keys atomicity: large number of keys in one flush	❌ Missing	Tests that atomicity holds beyond 3 keys; reviewer's derivation logic suggests boundary testing
Type-heterogeneous atomicity: multiple types in one atomic flush	Partial	Covered by TestAllValueTypes under supported_datatypes, but not explicitly linked to atomic_store
Verdict: The "or-nothing" negative path is tested, the happy path is tested, but the multi-instance case is not. Per the reviewer's principle: what if Instance 1's atomic flush somehow writes partial data into Instance 2's snapshot? That is exactly the kind of isolation question at FIT level that CIT doesn't answer.

Summary of Gaps
Requirement	Multi-instance covered	Other gaps
reset_resistant	✅ Yes	snapshot_max_count=1 edge case
recovery_from_reset	❌ No	Multi-instance recovery; recovery from N-th flush; fresh-start case
atomic_store	❌ No	Multi-instance atomic flush; many-key boundary
The reviewer's reasoning is systematic: for any ASIL_B durability requirement about persistence, the integration test must answer "does this hold when multiple KVS instances share the same storage directory?" This is the specific isolation property that CIT cannot verify (it tests one instance at a time through the API) and that FIT must verify by observing the actual filesystem state.

reset_resistant is the only one of the three requirements where this principle is already applied. recovery_from_reset and atomic_store each need a multi-instance variant added to the implementation.
