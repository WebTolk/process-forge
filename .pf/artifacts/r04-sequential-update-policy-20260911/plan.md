# R04 plan

1. Remove all tracked `dist/` release outputs; release packaging remains an
   explicit generated artifact step.
2. Move the `workplace_migration` pending operation and execution after Core
   files and manifest are written.
3. Update migration failure regression to require an incomplete manual-repair
   state and prove Core manifest is already at the target version.
4. Document serial Core → Workplace → project-work ordering in English and
   Russian; add a bounded junior shell-worker review after implementation.