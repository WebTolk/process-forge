# Run Plan: Runtime daemon lifecycle redesign

Objective: Audit the current long-lived Runtime lifecycle, remove incidental recovery choreography, and implement a small explicit background-daemon lifecycle without duplicating PF Core authority.
