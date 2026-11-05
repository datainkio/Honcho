---
pm-task: true
projectId: "[[context/Honcho Dev/Honcho Dev|Honcho Dev]]"
parentId:
id: 85l41z4zh6qlj9i5
title: "Fix match_packet batch file names colliding"
type: task
status: todo
priority: "medium"
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

# Fix match_packet batch file names colliding

`pipeline/scripts/package/match_packet.py` line 292 names batch files to the second, so packets built together overwrite each other. Add a pid or uuid.

Until then, build packets one at a time, 2 seconds apart.
