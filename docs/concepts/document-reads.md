# Reusing YAML parsing

PF keeps YAML files authoritative. The common document reader still opens the
current file before choosing a parsed result. Identical size or modification
time never proves that content is unchanged; deleting, replacing or editing a
file is observed on the next read. Authorization, byte fingerprints, capsule
validation and file-containment checks are not cached by this mechanism.

Within a running process, safe parse results can be reused across requests.
Keys include a SHA256 of the decoded content and the current safe parser,
constructor and resolver policy. Results returned to callers are independent
copies, preserving YAML aliases within each result. Parse failures and custom
stateful loader/constructor policies bypass shared retention. Existing legacy
fallback behavior remains with the caller's document reader.

The shared LRU retains at most 4096 entries, an estimated 64 MiB of values and
keys, and 2 MiB per entry. These are cache-retention limits, not a process RSS
limit or an input-file size limit. Large or unsupported value graphs are
returned without retention. Parsing and copying occur outside the cache lock;
simultaneous cold reads may parse the same input more than once.

Run discovery requests only `id`, `status` and the existing error marker after
the whole input has been validated. Its cache retains those fields rather than
the growing history. Full document reads continue to return complete data.
Cold parsing and reading/hash-checking current contents still cost work; this
does not replace a durable runtime-state index or migrate Work YAML to SQL.

## Shared Work metadata

`work/metadata.py` owns an explicit `WorkMetadataReadPass`. In `pf.context`,
the Work summary and automatic selection share this pass. It observes sorted
Run paths and reads compact Run/Assignment fields lazily in the consumer's
original order. Returned documents are independent copies. The summary and
catalog retain their different activity, fallback, ordering and selection rules.

Each new operation gets a fresh pass and reads current file contents before
reusing a parsed projection. Native catalog factories create passes lazily;
injected full record readers keep their existing path. A shared pass belongs to
one read operation and must be released before a write or a later request. There
is no request-wide Work snapshot, TTL, required watcher or writer invalidation
protocol. Different processes keep separate parse caches and observe changes
through their next current-content reads.

Completion journal paths come from their existing owner and are checked even
for terminal runs. Where a journal exists,
its existing validator receives full current Run/Assignment documents. Exact
canonical selectors retain their short path and final full live reads. Scope,
capsules, pins, source bytes, evidence and readiness are validated by their
existing owners rather than stored as authority in the metadata pass.

Custom document readers and unusual documents with no selected fields retain
the original full-read behavior. The existing bounded parser cache holds normal
compact projections between requests; the pass itself is released after the
operation. Cold or changed documents still require complete safe YAML parsing,
and current-content reads remain linear. This is a RAM optimization, without a
new durable index or an atomic transaction across externally written files.

The common path serves project/process/resource/Work readers and Runtime
metrics. Configuration's strict loader and live configuration resolver,
one-shot archive/update validation and other distinct validation boundaries
retain their own contracts. Host's session/deferred-conversation JSON state is
a separate owner and is not optimized by YAML parse reuse.

Implementation references: [Python copy](https://docs.python.org/3.14/library/copy.html),
[OrderedDict](https://docs.python.org/3.14/library/collections.html#ordereddict-objects),
[PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation).
