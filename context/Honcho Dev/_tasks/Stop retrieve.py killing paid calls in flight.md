---
pm-task: true
projectId: "[[context/Honcho Dev/Honcho Dev|Honcho Dev]]"
parentId:
id: wu3p4ggvsu126fkx
title: "Stop retrieve.py killing paid calls in flight"
type: task
status: todo
priority: "high"
start: ""
due: ""
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: []
createdAt: 2026-11-05T14:55:56.000Z
updatedAt: 2026-11-05T14:55:56.000Z
customFields: {}
---

# Stop retrieve.py killing paid calls in flight

`pipeline/scripts/retrieve.py`: one source's hard stop terminates the others, including a paid call mid-response. On 2026-11-05 Fantastic's 403 killed TheirStack before it wrote a record, so credits may have been spent with nothing saved, and the same-day guard won't block a repeat.

Done when a hard stop lets a paid call finish and save its record, or doesn't start one, and a test covers it.
