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

The common path serves project/process/resource/Work readers and Runtime
metrics. Configuration's strict loader and live configuration resolver,
one-shot archive/update validation and other distinct validation boundaries
retain their own contracts. Host's session/deferred-conversation JSON state is
a separate owner and is not optimized by YAML parse reuse.

Implementation references: [Python copy](https://docs.python.org/3.14/library/copy.html),
[OrderedDict](https://docs.python.org/3.14/library/collections.html#ordereddict-objects),
[PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation).
