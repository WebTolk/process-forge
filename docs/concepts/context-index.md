# Context Index

The Context Index is the compact source map for a ProcessForge session. It lists
the files that matter for the current session and records source fingerprints.

## Purpose

The index prevents agents from loading the whole project by habit. It tells them
which sources are required, optional, public, private, cached, or assignment
specific.

## Contents

A context index includes:

- context id and generated timestamp
- session mode
- project flow path
- source records with kind, path, required flag, checksum, and existence
- selected processes, packages, templates, tools, and capabilities
- freshness metadata

Source paths should be relative to the project root whenever possible.

## Freshness

The index is fresh when every required source still exists and has the same
checksum. If any required source changes, the index is stale and should be
rebuilt before compiling assignment context.

## Use By Workers

Workers should read sources listed in their Execution Context Package or context
capsule. They should not treat the context index as permission to inspect every
file in the repository.
