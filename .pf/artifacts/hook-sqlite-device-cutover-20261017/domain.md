# Data ownership and invariants

The dev ZIP and Core manifest own executable distribution files. The native updater owns installed-file preimages, manifest replacement and update recovery state. Project journals and configuration are runtime/private state outside that ownership boundary.

Each project owns its normalized event database and raw hook database. SQL admission IDs represent logical events; retries sharing an ID do not become multiple logical events. For legacy repeated deliveries with identical bodies, preserve the first envelope and retain all original bytes/locations separately. If anything except the legacy receipt time differs, stop rather than choose a meaning.

Migration states importing and ready gate normal consumers. Both databases must pass native integrity and count checks. Project event history and raw retention remain independent configuration choices; migration retains existing history. Legacy raw shards contain multiple project owners and must be filtered by normalized project identity. A stopped Runtime alone does not prove every other writer stopped; process inventory, source hashes, managed lifecycle and no MCP mutations are required.

Runtime process identity and installed byte identity prove loaded-device provenance; actual connected MCP is a separate process. A fresh standalone MCP launch is only standalone evidence. CPU percentages use total device capacity on four logical processors, matching the retained before measurement.
