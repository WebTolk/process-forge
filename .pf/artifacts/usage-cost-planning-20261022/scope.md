# Brief and scope

Plan one provider-neutral local accounting capability for agent execution time, actual token usage and clearly qualified monetary valuation, across projects and down to PF Work/attempt where observed. Future clients: Control Center console/TUI, Codex plugin, optional remote Control Center REST synchronization. All clients use the same application queries and accounting semantics.

Now: verified source inventory, domain rules, proposed storage/read boundaries, phased implementation and concrete acceptance scenarios. Attach the finalized plan to existing open card `pf-task-token-usage-logs-20261020`. User requests design, not implementation. New planning Work completes only this planning cycle.

First implementation scope proposed for later authorization: local accounting store, qualified driver/host collectors, normalized usage/activity/valuation, CLI JSON plus task/project summaries. No TUI rewrite, plugin implementation, remote server, authentication framework, automatic pricing download, currency conversion or infrastructure changes. Existing Monitor is a future presentation client. Source qualification must cover interactive primary agents as well as managed workers; unsupported sources remain explicitly unsupported.

Constraints: file-only PF workflows continue to work without Runtime/network; project lifecycle YAML and capsules remain authoritative for Work; accounting is optional and must not grant permissions or change Work outcomes. Missing readings are unknown, not zero. Accounting failure must be visible and retryable without changing a successful worker into failure or fabricating measurements.

Design questions to settle in artifacts: trustworthy capture sources and source capabilities; stable project/attempt/source identity; exactly-once contribution under duplicate/replayed/cumulative streams; active versus elapsed time; actual charges versus tariff estimates; one local cross-project store; query coverage and future opt-in synchronization. Source/API qualification gaps become explicit implementation gates, not assumptions of support.
