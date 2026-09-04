# Pygit Improvements Roadmap

> A prioritized backlog for improving Pygit after the first working version.
>
> **Goal:** improve correctness, safety, testability, and Git-internals fidelity without turning the project into an endless attempt to reimplement all of Git.

---

## Priority Legend

| Priority | Meaning |
|---|---|
| 🔴 **S** | Critical / high impact. Should be done first. |
| 🟠 **A** | Very important. Do after the S-tier work. |
| 🟡 **B** | Valuable improvement, but not urgent. |
| 🟢 **C** | Advanced / optional / deep Git internals. |

---

# 🔴 S-TIER: Correctness & Safety

## 1. Add a Real Test Suite

**Priority:** 🔴 S  
**Impact:** ⭐⭐⭐⭐⭐  
**Area:** Entire project  
**Suggested location:** `tests/`

### Problem

Pygit currently has no serious automated test suite covering the complete behavior of the VCS.

This is the biggest gap because adding features without tests makes it difficult to know whether existing behavior still works.

A Git-like system has many interacting components:

```text
objects
   ↓
trees
   ↓
commits
   ↓
refs
   ↓
branches
   ↓
checkout
   ↓
merge
   ↓
remote
```

A bug in one layer can appear as a bug somewhere completely different.

### Improvement

Create both:

1. **Unit tests** for individual functions.
2. **Integration tests** for realistic Git workflows.

### Test areas

#### Object storage
- Hashing an object produces the expected OID.
- Writing and reading an object returns identical data.
- Different content produces different OIDs.
- Blob/tree/commit types are preserved.
- Missing objects produce a controlled error.
- Corrupt objects are detected once integrity checking is implemented.

#### Index
- `add` creates the correct index entries.
- Multiple files are stored correctly.
- Nested directories work.
- Updating a file updates its OID.
- Removed files are handled correctly.

#### Trees
- `write_tree()` creates the correct hierarchy.
- Nested directories produce nested trees.
- Tree contents are deterministic.
- Identical trees produce identical OIDs.

#### Commits
- First commit has no parent.
- Normal commit has one parent.
- Merge commit has two parents.
- Commit points to the correct tree.
- Commit OIDs change when commit content changes.

#### Refs
- `HEAD` works.
- Branch creation works.
- Branch movement works.
- Symbolic HEAD works.
- Detached HEAD works.

#### Checkout
- Checkout reconstructs the correct working tree.
- Branch checkout updates HEAD.
- Detached checkout works.
- Switching between commits restores old versions.

#### Merge
Test at least:

```text
fast-forward
clean 3-way merge
conflicting 3-way merge
HEAD == OTHER
BASE == HEAD
BASE == OTHER
delete/delete
delete/modify
modify/modify
new/new
```

#### Remote

```text
push to empty remote
push fast-forward
reject non-fast-forward push
fetch
fetch missing objects
fetch existing objects
```

### Integration test example

A very valuable test is:

```text
init
  ↓
create file
  ↓
add
  ↓
commit A
  ↓
modify file
  ↓
add
  ↓
commit B
  ↓
checkout A
  ↓
assert file == old content
```

This tests the actual version-control behavior instead of isolated functions.

### Definition of Done

- [ ] `tests/` exists.
- [ ] Core object operations are tested.
- [ ] Commit/branch/checkout workflow is tested.
- [ ] Merge behavior has a dedicated test matrix.
- [ ] Remote behavior has integration tests.
- [ ] Tests run with one command.
- [ ] Tests pass before and after future refactors.

---

# 2. Make Checkout Safe

**Priority:** 🔴 S  
**Impact:** ⭐⭐⭐⭐⭐  
**File:** `pygit/base.py`  
**Main functions:** `checkout()`, `_empty_current_directory()`, `read_tree()`

### Problem

`checkout()` can replace the working tree without first making sure that local/untracked changes are safe.

The dangerous scenario is:

```text
working tree:
    hello.txt = "my important local changes"

target commit:
    hello.txt = "old version"
```

A checkout should not silently destroy the local version.

### Improvement

Before checkout:

1. Determine the target tree.
2. Compare current working-tree state against the index.
3. Determine which files would be overwritten/deleted.
4. Refuse checkout if local changes would be lost.
5. Add a `--force` option later if desired.

Desired behavior:

```text
$ pygit checkout feature

error: Your local changes would be overwritten by checkout.
```

And optionally:

```text
$ pygit checkout --force feature
```

### Important architectural point

Do not solve this by simply adding another `assert`.

This is a normal runtime condition and deserves a proper exception.

### Definition of Done

- [ ] Checkout detects files that would be overwritten.
- [ ] Checkout detects relevant untracked files.
- [ ] Checkout refuses destructive operations by default.
- [ ] A force option can intentionally bypass the protection.
- [ ] Tests cover safe and unsafe checkout.

---

# 3. Fix Merge Edge Cases

**Priority:** 🔴 S  
**Impact:** ⭐⭐⭐⭐⭐  
**File:** `pygit/diff.py`  
**Main function:** `merge_trees()`

### Problem

The current merge logic can attempt a three-way merge even when a simpler answer already exists.

Important cases:

```text
BASE == HEAD
BASE == OTHER
HEAD == OTHER
```

These cases should not require an actual content merge.

### Correct behavior

#### Case 1

```text
BASE == HEAD
```

HEAD did not change, so:

```text
result = OTHER
```

#### Case 2

```text
BASE == OTHER
```

Other did not change, so:

```text
result = HEAD
```

#### Case 3

```text
HEAD == OTHER
```

Both sides are identical:

```text
result = HEAD
```

Only when both sides changed differently should an actual merge be attempted.

### Merge conflict matrix

You should explicitly handle:

```text
                 OTHER
              unchanged   changed
            +------------+------------+
HEAD same   | same       | take other |
            +------------+------------+
HEAD change | take head  | merge      |
            +------------+------------+
```

Also test:

- file added on both sides
- file deleted on one side
- file modified on one side
- file deleted on one side and modified on the other
- directory/file conflicts
- both sides create different versions of the same file

### Definition of Done

- [ ] Fast/simple merge cases bypass `merge_blobs`.
- [ ] Conflict cases are detected.
- [ ] Delete/modify is handled intentionally.
- [ ] New/new is handled intentionally.
- [ ] Every edge case has a regression test.

---

# 4. Implement a Proper Merge Base

**Priority:** 🔴 S  
**Impact:** ⭐⭐⭐⭐⭐  
**File:** `pygit/base.py`  
**Main function:** `get_merge_base()`

### Problem

The current implementation finds a common ancestor, but a complex commit DAG can have multiple common ancestors.

Finding *a* common ancestor is not always the same as finding the correct/best merge base.

Git history is a DAG:

```text
       A
      / \
     B   C
      \ /
       D
```

And real histories can be significantly more complicated because of repeated merges.

### Improvement

Implement merge-base logic that:

1. Walks ancestors of both commits.
2. Finds common ancestors.
3. Eliminates ancestors that are themselves ancestors of another common ancestor.
4. Returns the best relevant common ancestor according to the chosen semantics.

### Why this matters

The merge base determines the `BASE` used by:

```text
BASE + HEAD + OTHER
```

If BASE is wrong, the resulting merge can be wrong even if the rest of the merge algorithm is perfect.

### Definition of Done

- [ ] Multiple-parent commits are handled.
- [ ] Complex DAGs are tested.
- [ ] Multiple common ancestors are tested.
- [ ] The selected merge base is deterministic.
- [ ] Regression tests exist for previously broken histories.

---

# 🟠 A-TIER: Reliability & User Experience

## 5. Replace `assert` With Proper Exceptions

**Priority:** 🟠 A  
**Impact:** ⭐⭐⭐⭐  
**Files:** Mainly `pygit/base.py`, `pygit/remote.py`

### Problem

The code currently uses `assert` for runtime/user validation.

Example pattern:

```python
assert condition
```

This is not appropriate for normal application errors.

Python can disable assertions with:

```bash
python -O
```

That means validation implemented through `assert` can disappear.

### Improvement

Create a custom exception hierarchy.

For example:

```python
class PygitError(Exception):
    pass

class RepositoryError(PygitError):
    pass

class CheckoutError(PygitError):
    pass

class MergeError(PygitError):
    pass

class ObjectError(PygitError):
    pass

class RefError(PygitError):
    pass
```

Then:

```python
if not condition:
    raise CheckoutError("local changes would be overwritten")
```

### Definition of Done

- [ ] Runtime validation no longer depends on `assert`.
- [ ] Core errors use meaningful exception classes.
- [ ] CLI converts expected exceptions into readable messages.
- [ ] Assertions remain only for genuine programmer invariants, if any.

---

# 6. Centralized CLI Error Handling

**Priority:** 🟠 A  
**Impact:** ⭐⭐⭐⭐  
**File:** `pygit/cli.py`

### Problem

An unexpected/expected exception can currently result in a Python traceback instead of a clean CLI error.

### Improvement

Wrap command execution:

```text
command
   ↓
core logic
   ↓
PygitError
   ↓
CLI handler
   ↓
error: <message>
   ↓
non-zero exit code
```

Example:

```text
$ pygit checkout does-not-exist

error: unknown revision 'does-not-exist'
```

Instead of exposing an implementation traceback.

### Definition of Done

- [ ] Expected errors are caught centrally.
- [ ] Messages are concise.
- [ ] Exit codes are non-zero on failure.
- [ ] Unexpected programming errors can still expose useful debugging information during development.

---

# 7. Make `change_git_dir()` Exception-Safe

**Priority:** 🟠 A  
**Impact:** ⭐⭐⭐  
**File:** `pygit/data.py`  
**Function:** `change_git_dir()`

### Problem

`GIT_DIR` is global state.

If an exception occurs while inside the context manager and the old value is not restored, future operations can point to the wrong repository.

### Improvement

Use:

```python
old_git_dir = GIT_DIR

try:
    GIT_DIR = ...
    yield
finally:
    GIT_DIR = old_git_dir
```

### Longer-term improvement

Eventually consider replacing the global repository state with a repository object:

```python
repo = Repository("/path/to/repo")
repo.commit(...)
repo.checkout(...)
```

This would make the architecture easier to test and reason about.

### Definition of Done

- [ ] `GIT_DIR` always restores after exceptions.
- [ ] Test exists specifically for exception paths.

---

# 8. Verify Object Integrity

**Priority:** 🟠 A  
**Impact:** ⭐⭐⭐⭐  
**File:** `pygit/data.py`  
**Functions:** `hash_object()`, `get_object()`

### Problem

Objects are content-addressed using SHA-1:

```text
object content
      ↓
header + content
      ↓
SHA-1
      ↓
OID
```

But when loading an object, the implementation should ideally verify that the content still corresponds to the requested OID.

Otherwise a corrupted object could be accepted.

### Improvement

On read:

```text
OID
 ↓
decompress object
 ↓
reconstruct header + data
 ↓
hash
 ↓
compare with OID
```

If different:

```text
error: corrupt object <oid>
```

### Additional improvements

- Validate object type.
- Validate object size.
- Remove or use the currently parsed `_size`.
- Avoid silently accepting malformed objects.

### Definition of Done

- [ ] Object hash is verified on read.
- [ ] Corruption raises a controlled exception.
- [ ] Object type is validated.
- [ ] Malformed headers are rejected.

---

# 🟡 B-TIER: Git Fidelity & Useful Features

## 9. Add Commit Metadata

**Priority:** 🟡 B  
**Impact:** ⭐⭐⭐  
**File:** `pygit/base.py`  
**Function:** `commit()`

### Current model

The commit currently contains the tree, parent(s), and message.

### Improvement

Add concepts similar to Git:

```text
tree
parent
author
committer

message
```

With information such as:

```text
name
email
timestamp
timezone
```

### Why

This makes the commit object much closer to the real Git object model.

It also makes:

```text
log
```

much more meaningful.

### Definition of Done

- [ ] Author information exists.
- [ ] Committer information exists.
- [ ] Timestamp is stored.
- [ ] Timezone is stored.
- [ ] `log` displays metadata.

---

# 10. Support Revision Expressions

**Priority:** 🟡 B  
**Impact:** ⭐⭐⭐  
**File:** `pygit/base.py`  
**Main function:** `get_oid()`

### Current behavior

Pygit resolves refs, branches, tags, and full OIDs.

### Improvement

Support:

```bash
pygit show HEAD
pygit show HEAD~1
pygit show HEAD~3
pygit show HEAD^
```

Potentially later:

```text
branch~2
branch^
```

### Why

Revision expressions are one of the nicest parts of Git's object model because they let users navigate the DAG without manually copying hashes.

### Definition of Done

- [ ] `HEAD~N`
- [ ] `HEAD^`
- [ ] branch-relative revisions
- [ ] invalid revision expressions fail cleanly
- [ ] tests for merge commits

---

# 11. Improve Commit Graph Traversal / Log Ordering

**Priority:** 🟡 B  
**Impact:** ⭐⭐⭐  
**File:** `pygit/base.py`  
**Function:** `iter_commits_and_parents()`

### Problem

The current traversal correctly walks the graph, but traversal order is not necessarily equivalent to Git's user-facing history ordering.

### Improvement

Implement a more deliberate graph traversal strategy.

Possible future features:

```text
--date-order
--topo-order
```

Not necessary for the first version, but useful if you want `log` to feel more Git-like.

### Definition of Done

- [ ] Traversal is deterministic.
- [ ] Merge commits are handled correctly.
- [ ] Ordering behavior is documented.
- [ ] Tests cover branching and merging histories.

---

# 12. Improve Reset Semantics

**Priority:** 🟡 B  
**Impact:** ⭐⭐⭐  
**File:** `pygit/base.py`

### Problem

Current `reset()` behavior is much simpler than Git's reset semantics.

### Possible future design

```bash
pygit reset --soft <commit>
pygit reset --mixed <commit>
pygit reset --hard <commit>
```

Conceptually:

```text
--soft
    move HEAD only

--mixed
    move HEAD + update index

--hard
    move HEAD + update index + working tree
```

### Warning

Do this only after checkout safety is implemented.

A `--hard` operation is intentionally destructive, so the behavior must be explicit.

---

# 🟢 C-TIER: Deep Git Internals

## 13. Implement a Git-Like Binary Index

**Priority:** 🟢 C  
**Impact:** ⭐⭐⭐  
**File:** `pygit/data.py`

### Current situation

Pygit stores the index as JSON.

That's completely reasonable for a learning implementation.

### Future challenge

Implement a binary index similar to Git's:

```text
header
entries
extensions
checksum
```

### What you'll learn

- binary file formats
- serialization
- checksums
- filesystem metadata
- performance considerations

This is a great "deep dive" project, but not necessary for Pygit's core correctness.

---

# 14. Add Reflog

**Priority:** 🟢 C  
**Impact:** ⭐⭐  
**Files:** `pygit/data.py`, `pygit/base.py`

### Idea

Track ref movements:

```text
HEAD moved A -> B
HEAD moved B -> C
HEAD moved C -> D
```

Then expose something like:

```bash
pygit reflog
```

### Why

Reflog teaches an important distinction:

```text
Git object database
        ≠
refs
        ≠
reflog
```

Objects can remain even after refs stop pointing at them.

---

# 15. Packfiles

**Priority:** 🟢 C  
**Impact:** ⭐⭐⭐⭐ for Git internals, ⭐ for basic Pygit

### Why it matters

Git doesn't keep every object forever as an individual loose file.

Eventually objects can be packed:

```text
loose objects
      ↓
pack
      ↓
delta compression
      ↓
.idx
```

### What you'll learn

- binary formats
- compression
- delta encoding
- object indexing
- storage optimization

### Recommendation

Do this only if the goal becomes:

> "I want to deeply understand Git internals."

Do not do it just because "Git has packfiles."

---

# 16. Real Remote Protocol

**Priority:** 🟢 C  
**Impact:** ⭐⭐⭐⭐ for networking/Git internals

### Current situation

Pygit's remote implementation uses the filesystem.

That is a perfectly reasonable educational first step.

### Future direction

Eventually investigate:

```text
transport
    ↓
negotiation
    ↓
object discovery
    ↓
pack transfer
    ↓
ref update
```

Potentially explore Git's actual protocols later.

### Recommendation

This should be one of the last improvements.

---

# Architecture Improvements

## Current Architecture

The current separation is already reasonable:

```text
cli.py
  │
  ▼
base.py
  │
  ├──────────────┐
  ▼              ▼
data.py        diff.py
  │
  ▼
objects/index/refs

remote.py
  │
  ▼
remote repositories
```

### Keep this architecture for now

Do not rewrite everything just for the sake of architecture.

The current project is small enough that a full rewrite would probably produce more churn than value.

---

## Future Architecture: Repository Object

Eventually, instead of global:

```python
GIT_DIR
```

consider:

```python
repo = Repository(path)
```

Then:

```python
repo.add(...)
repo.commit(...)
repo.checkout(...)
repo.merge(...)
```

This would improve:

- testability
- multiple repositories in one process
- dependency management
- separation of state
- readability

But this is a **future refactor**, not a first priority.

---

# Documentation Improvements

## Add `CONTRIBUTING.md`

Explain:

```text
How to set up development environment
How to run tests
How to format/lint
How to add a command
How objects work
How merges work
```

---

## Add an Architecture Diagram

Document:

```text
Working Tree
     │
     ▼
   Index
     │
     ▼
   Trees
     │
     ▼
   Commits
     │
     ▼
    Refs
```

And:

```text
Commit
 ├── tree → Tree
 ├── parent → Commit
 └── parent → Commit
```

This makes the Merkle DAG concept immediately visible.

---

# Code Quality Improvements

After the correctness work:

## Formatting

Consider:

```text
ruff
black
```

or one consistent formatter/linter setup.

## Type hints

Gradually add:

```python
def get_oid(name: str) -> str:
    ...
```

Don't type-hint the entire project in one giant refactor.

## CI

Add GitHub Actions to automatically run:

```text
tests
lint
type checking
```

on every push/PR.

---

# Recommended Execution Plan

Do NOT implement everything in one giant branch.

Use milestones.

## Phase 1: Make Pygit Harder to Break

- [ ] Add test framework.
- [ ] Add object tests.
- [ ] Add tree tests.
- [ ] Add commit/ref tests.
- [ ] Add checkout integration tests.
- [ ] Add merge tests.
- [ ] Add remote tests.

**Goal:** establish a safety net before modifying core behavior.

---

## Phase 2: Fix Dangerous / Incorrect Behavior

- [ ] Make checkout safe.
- [ ] Fix merge edge cases.
- [ ] Implement proper merge-base.
- [ ] Replace runtime asserts with exceptions.
- [ ] Make `change_git_dir()` exception-safe.
- [ ] Add object integrity validation.

**Goal:** correctness first.

---

## Phase 3: Improve User Experience

- [ ] Centralized CLI error handling.
- [ ] Better error messages.
- [ ] Proper exit codes.
- [ ] Improve `log`.
- [ ] Clean up CLI naming/help text.
- [ ] Make `vis` output more portable.

---

## Phase 4: Improve Git Fidelity

- [ ] Commit metadata.
- [ ] Revision expressions.
- [ ] Better graph traversal.
- [ ] Better reset semantics.

**Goal:** make Pygit behave more like Git without losing its educational simplicity.

---

## Phase 5: Deep Git Internals

Only if you still want to continue:

- [ ] Binary index.
- [ ] Reflog.
- [ ] Packfiles.
- [ ] Delta compression.
- [ ] Real remote protocol.

**Goal:** learn Git internals at a much deeper level.

---

# Final Priority Order

If you only have limited free time, follow this exact order:

```text
1.  🔴 Tests
2.  🔴 Checkout safety
3.  🔴 Merge edge cases
4.  🔴 Proper merge-base
5.  🟠 Replace runtime asserts
6.  🟠 CLI error handling
7.  🟠 Exception-safe GIT_DIR
8.  🟠 Object integrity checking
9.  🟡 Commit metadata
10. 🟡 Revision expressions
11. 🟡 Better lo