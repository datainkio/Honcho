---
cssclasses:
  - dashboard-layout
---

```dataviewjs

// --- ⚙️ PERSISTENCE ENGINE ---
const defaultHabitNames = ["Reading", "Coding", "Meditate", "Gym"];
let savedHabits = JSON.parse(localStorage.getItem("zos-final-habits")) || defaultHabitNames;
localStorage.setItem("zos-final-habits", JSON.stringify(savedHabits));

// Banner title & subtitle persistence
let bannerTitle = localStorage.getItem("zos-banner-title") || "DASHBOARD ZEN";
let bannerSubtitle = localStorage.getItem("zos-banner-subtitle") || "";

const container = dv.container.createDiv({ cls: "zos-dashboard animate-in" });

// --- 📋 APPLICATION DATA ---
// Packages are the folders under applications/ (not _tasks). Statuses are matched by label
// from the project note's config.statuses, so dotpm ids can change without breaking this.
const APPS_FOLDER = "applications";
const TASKS_FOLDER = "applications/_tasks";
const PROJECT_NOTE = "applications/DEFAULT.md";
const PROSPECT_LABELS = ["Prospect"];
const RESPONSE_LABELS = ["Screening", "Interviewing", "Finalist", "Offer", "Accepted", "Rejected", "Withdrawn"];
// Submitted = waiting on a reply (Applied, Unresponsive) or replied (RESPONSE_LABELS).
const SUBMITTED_LABELS = ["Applied", "Unresponsive", ...RESPONSE_LABELS];

let responseGoal = 0; // fraction, 0–1 (honcho.yaml: obsidian.response-goal)
try {
    // No YAML parser is reachable from dataviewjs: read the key from the top-level obsidian: block.
    const yaml = await app.vault.adapter.read("honcho.yaml");
    const block = (yaml.match(/^obsidian:\s*\n((?:[ \t]+.*\n?|\s*\n)*)/m) || [])[1] || "";
    const g = Number((block.match(/^[ \t]+response-goal:\s*["']?([0-9.]+)/m) || [])[1]);
    if (Number.isFinite(g)) responseGoal = g > 1 ? g / 100 : g;
} catch (e) { console.warn("dashboard: could not read honcho.yaml response-goal", e); }

// Global pointers for dynamic updates
let bioBar, bioText, bioInfoEl, taskBar, taskText, taskTitleEl;

const Utils = {
    getGreeting: () => {
        const h = new Date().getHours();
        if (h < 5) return "Night of Stillness 🌙";
        if (h < 12) return "Morning Clarity ☀️";
        if (h < 18) return "Deep Focus ⚡";
        return "End of Day 🌌";
    },


    getPackageCount: () => {
        const root = app.vault.getAbstractFileByPath(APPS_FOLDER);
        return root?.children ? root.children.filter(c => c.children && !c.name.startsWith("_")).length : 0;
    },
    statusIds: (labels) => {
        const f = app.vault.getAbstractFileByPath(PROJECT_NOTE);
        const statuses = (f && app.metadataCache.getFileCache(f)?.frontmatter?.config?.statuses) || [];
        return new Set(statuses.filter(s => labels.includes(s.label)).map(s => s.id));
    },
    countByStatus: (labels) => {
        const ids = Utils.statusIds(labels);
        return dv.pages(`"${TASKS_FOLDER}"`).where(p => ids.has(String(p.status))).length;
    },
    getReadyProspects: () => {
        const ids = Utils.statusIds(PROSPECT_LABELS);
        return dv.pages(`"${TASKS_FOLDER}"`)
            .where(p => ids.has(String(p.status)) && Number(p.progress) === 100)
            .sort(p => p.due, "asc");
    },
    getResponseStats: () => {
        const responded = Utils.countByStatus(RESPONSE_LABELS);
        const submitted = Utils.countByStatus(SUBMITTED_LABELS);
        const percent = submitted > 0 ? (responded / submitted) * 100 : 0;
        return { responded, submitted, percent };
    },
    getHabitStats: () => {
        let totalDots = savedHabits.length * 7;
        let activeDots = 0;
        savedHabits.forEach(h => {
            for(let i=1; i<=7; i++) {
                if(localStorage.getItem(`zos-v28-h-${h}-${i}`)) activeDots++;
            }
        });
        const perf = totalDots > 0 ? (activeDots / totalDots) * 100 : 0;
        return { total: totalDots, active: activeDots, percent: perf };
    },
    updateBars: () => {
        const hStats = Utils.getHabitStats();
        if (bioBar) bioBar.style.width = `${hStats.percent}%`;
        if (bioText) bioText.innerText = `Weekly Consistency: ${hStats.percent.toFixed(0)}%`;
        if (bioInfoEl) bioInfoEl.innerHTML = `Completed: <b>${hStats.active}</b> of <b>${hStats.total}</b> points.<br>${hStats.percent >= 80 ? "🔥 Elite performance detected." : "🚀 Keep maintaining your focus."}` ;
        
        const r = Utils.getResponseStats();
        if (taskBar) {
            taskBar.style.width = `${Math.min(r.percent, 100)}%`;
            taskBar.style.background = r.percent >= responseGoal * 100 ? "#00ff88" : "#e0b04a";
        }
        if (taskText) taskText.innerText = `Response Rate: ${r.percent.toFixed(0)}% (${r.responded} of ${r.submitted} submitted)`;
        
        renderTasks();
    },
    showModal: ({ title, value, onSave, onDelete, placeholder, type = "text", options = [] }) => {
        const overlay = document.body.createDiv({ cls: "zos-modal-overlay" });
        const modal = overlay.createDiv({ cls: "zos-modal" });
        
        modal.createDiv({ cls: "zos-modal-title", text: title });
        
        const close = () => overlay.remove();

        if (type === "text") {
            const input = modal.createEl("input", { 
                cls: "zos-modal-input", 
                attr: { type: "text", value: value || "", placeholder: placeholder || "Type here..." }
            });
            input.focus(); input.select();
            
            const btns = modal.createDiv({ cls: "zos-modal-btns" });
            const row = btns.createDiv({ cls: "zos-modal-row" });
            const cancelBtn = row.createEl("button", { cls: "zos-modal-btn zos-btn-cancel", text: "Cancel" });
            const saveBtn = row.createEl("button", { cls: "zos-modal-btn zos-btn-save", text: "Save" });
            
            cancelBtn.onclick = close;
            saveBtn.onclick = () => { onSave(input.value); close(); };
            input.onkeydown = (e) => { if(e.key === "Enter") saveBtn.click(); if(e.key === "Escape") close(); };
            if (onDelete) {
                const deleteBtn = btns.createEl("button", { cls: "zos-modal-btn zos-btn-delete", text: "🗑️ Delete Habit", attr: { style: "width: 100%; margin-top: 8px;" } });
                deleteBtn.onclick = () => { onDelete(); close(); };
            }
        } else if (type === "grid") {
            const gridCont = modal.createDiv({ attr: { style: "display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 20px;" } });
            options.forEach(opt => {
                const btn = gridCont.createEl("button", { 
                    cls: "zos-modal-btn", 
                    text: opt.label,
                    attr: { style: "background: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); text-align: left; padding: 15px; font-weight: 600;" }
                });
                btn.onclick = () => { onSave(opt.value); close(); };
                btn.onmouseenter = () => { btn.style.background = "rgba(var(--zos-accent-rgb), 0.1)"; btn.style.borderColor = "var(--zos-accent)"; };
                btn.onmouseleave = () => { btn.style.background = "rgba(255,255,255,0.05)"; btn.style.borderColor = "rgba(255,255,255,0.1)"; };
            });
            modal.createEl("button", { cls: "zos-modal-btn zos-btn-cancel", text: "Close", attr: { style: "width: 100%" } }).onclick = close;
        } else if (type === "suggest") {
            const search = modal.createEl("input", { cls: "zos-modal-input", attr: { placeholder: "Search..." } });
            const listCont = modal.createDiv({ attr: { style: "max-height: 250px; overflow-y: auto; background: #111; border-radius: 12px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05);" } });
            
            const renderList = (filter = "") => {
                listCont.innerHTML = "";
                const filtered = options.filter(o => o.label.toLowerCase().includes(filter.toLowerCase())).slice(0, 40);
                if (filtered.length === 0) listCont.createDiv({ text: "No results", attr: { style: "padding: 20px; text-align: center; opacity: 0.3;" } });
                filtered.forEach(opt => {
                    const item = listCont.createDiv({ 
                        text: opt.label, 
                        attr: { style: "padding: 12px 15px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.03); color: #fff; font-size: 0.9em;" } 
                    });
                    item.onmouseenter = () => item.style.background = "rgba(var(--zos-accent-rgb), 0.1)";
                    item.onmouseleave = () => item.style.background = "transparent";
                    item.onclick = () => { onSave(opt.value); close(); };
                });
            };
            
            search.oninput = () => renderList(search.value);
            renderList();
            search.focus();
            modal.createEl("button", { cls: "zos-modal-btn zos-btn-cancel", text: "Close", attr: { style: "width: 100%" } }).onclick = close;
        }
        
        overlay.onclick = (e) => { if(e.target === overlay) close(); };
    }
};

let taskSourceIndicator;


// --- RENDER HEADER ---
const header = container.createDiv({ cls: "zos-header" });
const hero = header.createDiv({ cls: "zos-hero-text" });

const heroTitleEl = hero.createEl("h1", { 
    text: bannerTitle, 
    attr: { style: "font-size: 3.5em; font-weight: 900; letter-spacing: -2px; margin-bottom: 5px; background: linear-gradient(to right, #fff, rgba(255,255,255,0.4)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;" } 
});

const heroSubtitleEl = hero.createDiv({ 
    text: bannerSubtitle || `${Utils.getGreeting()} — Welcome back. The entire system is ready. ✨`, 
    attr: { style: "opacity: 0.6; font-size: 1.1em; letter-spacing: 0.5px;" }
});

// Botón ⚙️ del banner (hijo del header, esquina superior derecha)
const bannerSettingsBtn = header.createDiv({ cls: "zos-banner-settings-btn" });
try { setIcon(bannerSettingsBtn, "settings"); } catch(e) { bannerSettingsBtn.innerText = "⚙️"; }

bannerSettingsBtn.onclick = () => {
    Utils.showModal({
        title: "Edit Banner",
        type: "grid",
        options: [
            { label: "✏️  Edit Title", value: "title" },
            { label: "💬  Edit Subtitle", value: "subtitle" }
        ],
        onSave: (choice) => {
            if (choice === "title") {
                Utils.showModal({
                    title: "Dashboard Title",
                    value: bannerTitle,
                    placeholder: "E.g.: MY DASHBOARD",
                    onSave: (val) => {
                        if (val.trim()) {
                            bannerTitle = val.trim().toUpperCase();
                            localStorage.setItem("zos-banner-title", bannerTitle);
                            heroTitleEl.innerText = bannerTitle;
                        }
                    }
                });
            } else if (choice === "subtitle") {
                Utils.showModal({
                    title: "Banner Subtitle",
                    value: bannerSubtitle || `${Utils.getGreeting()} — Welcome back. The entire system is ready. ✨`,
                    placeholder: "E.g.: Welcome back ✨",
                    onSave: (val) => {
                        bannerSubtitle = val.trim();
                        localStorage.setItem("zos-banner-subtitle", bannerSubtitle);
                        heroSubtitleEl.innerText = bannerSubtitle || `${Utils.getGreeting()} — Welcome back. The entire system is ready. ✨`;
                    }
                });
            }
        }
    });
};

const statsCont = header.createDiv({ cls: "zos-hero-stats" });
function renderHeroStats() {
    statsCont.innerHTML = "";
    [
        { v: Utils.getPackageCount(), l: "Applications", i: "briefcase" },
        { v: Utils.countByStatus(PROSPECT_LABELS), l: "Prospects", i: "telescope" }
    ].forEach(stat => {
        const cube = statsCont.createDiv({ cls: "zos-stat-cube" });
        const topRow = cube.createDiv({ attr: { style: "display: flex; align-items: center; justify-content: flex-end; gap: 10px;" }});
        const iCont = topRow.createDiv();
        try { setIcon(iCont, stat.i); } catch(e) { iCont.innerText = "⭐"; }
        topRow.createDiv({ cls: "zos-stat-val", text: stat.v.toString() });
        cube.createDiv({ cls: "zos-stat-lab", text: stat.l });
    });
}
renderHeroStats();

// --- MAIN GRID ---
const grid = container.createDiv({ cls: "zos-grid" });

// --- LEFT COLUMN ---
const colLeft = grid.createDiv({ cls: "span-4" });

// Modulo: Sistema
const cardActions = colLeft.createDiv({ cls: "zos-card" });
cardActions.createDiv({ cls: "zos-card-title", text: "🛠️ SYSTEM" });
const aGrid = cardActions.createDiv({ attr: { style: "display: grid; grid-template-columns: 1fr 1fr; gap: 15px;" }});

const ops = [
    { n: "Daily", icon: "calendar", em: "📅", cmd: "daily-notes" },
    { n: "Search", icon: "search", em: "🔍", cmd: "global-search:open" },
    { n: "Graph", icon: "share-2", em: "🕸️", cmd: "graph:open" },
    { n: "New", icon: "plus-circle", em: "➕", cmd: "file-explorer:new-file" }
];

ops.forEach(op => {
    const btn = aGrid.createDiv({ cls: "zos-action-btn" });
    const iconCont = btn.createDiv();
    try { 
        const { setIcon } = require("obsidian");
        setIcon(iconCont, op.icon); 
    } catch(e) { 
        iconCont.innerText = op.em; 
    }
    btn.createDiv({ text: op.n.toUpperCase(), attr: { style: "font-size: 0.7em; font-weight: 700; margin-top: 5px;" }});
    btn.onclick = () => app.commands.executeCommandById(op.cmd);
});

// Card: Bio-Performance
const cardBioPerf = colLeft.createDiv({ cls: "zos-card", attr: { style: "margin-top: 32px;" } });
cardBioPerf.createDiv({ cls: "zos-card-title", text: "📈 BIO-PERFORMANCE" });

const hStats = Utils.getHabitStats();
bioText = cardBioPerf.createDiv({ 
    text: `Weekly Consistency: ${hStats.percent.toFixed(0)}%`, 
    attr: { style: "font-size: 1.1em; font-weight: 600; margin-bottom: 10px;" } 
});

const bioBarBg = cardBioPerf.createDiv({ attr: { style: "height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; margin-bottom: 15px;" }});
bioBar = bioBarBg.createDiv({ attr: { style: `height: 100%; width: ${hStats.percent}%; background: #00ff88; box-shadow: 0 0 10px rgba(0,255,136,0.3); transition: width 0.6s ease;` }});

bioInfoEl = cardBioPerf.createDiv({ attr: { style: "font-size: 0.75em; opacity: 0.6; line-height: 1.4;" } });
bioInfoEl.innerHTML = `Completed: <b>${hStats.active}</b> of <b>${hStats.total}</b> points.<br>${hStats.percent >= 80 ? "🔥 Elite performance detected." : "🚀 Keep maintaining your focus."}` ;

// --- RIGHT COLUMN ---
const colCenter = grid.createDiv({ cls: "span-8" });

// Pipeline Card: Prospects whose package is complete (progress 100), ready to submit
const cardTasks = colCenter.createDiv({ cls: "zos-card" });
const tHeader = cardTasks.createDiv({ cls: "zos-card-title", attr: { style: "justify-content: space-between;" } });
const tLeftHeader = tHeader.createDiv({ attr: { style: "display: flex; align-items: center; gap: 10px;" } });
tLeftHeader.createDiv({ text: "⚡ APPLICATION PIPELINE" });
taskSourceIndicator = tLeftHeader.createDiv({ cls: "zos-task-source-indicator" });

const taskListCont = cardTasks.createDiv({ attr: { style: "max-height: 340px; overflow-y: auto; padding-right: 4px;" } });
function renderTasks() {
    taskListCont.innerHTML = "";
    const ready = Utils.getReadyProspects();
    if (taskSourceIndicator) taskSourceIndicator.innerText = `${ready.length} READY`;
    if (ready.length > 0) {
        ready.forEach(p => {
            const overdue = p.due && p.due <= dv.date('today');
            const row = taskListCont.createDiv({ cls: "zos-task-row" });
            row.createDiv({ cls: "zos-task-check" });
            const body = row.createDiv({ attr: { style: "flex-grow: 1;" } });
            body.createDiv({ text: p.title || p.file.name, attr: { style: "font-weight: 600;" } });
            body.createDiv({ text: `Prospect · 100%${p.priority ? ` · ${p.priority}` : ""}`, attr: { style: "font-size: 0.7em; opacity: 0.5;" } });
            row.createDiv({
                cls: "zos-task-tag",
                text: p.due ? p.due.toLocaleString('es-ES', {day:'numeric', month:'short'}) : 'OPEN',
                attr: { style: overdue ? "background: #ff555522; color: #ff5555;" : "" }
            });
            row.onclick = () => app.workspace.openLinkText(p.file.path, "", false);
        });
    } else {
        taskListCont.createDiv({ cls: "zos-hint", text: "Nothing ready yet." });
    }
}
renderTasks();

// Response Rate Card (taskBar / taskText are refreshed by Utils.updateBars)
const cardHealth = colCenter.createDiv({ cls: "zos-card", attr: { style: "margin-top: 32px;" } });
cardHealth.createDiv({ cls: "zos-card-title", text: "📊 RESPONSE RATE" });

taskText = cardHealth.createDiv({ attr: { style: "font-size: 0.9em; margin-bottom: 12px; opacity: 0.7;" } });
const goalPct = Math.min(Math.max(responseGoal * 100, 0), 100);
const barWrap = cardHealth.createDiv({ attr: { style: "position: relative; padding-top: 20px;" } });
const barBg = barWrap.createDiv({ attr: { style: "height: 8px; background: rgba(255,255,255,0.05); border-radius: 6px; overflow: hidden;" }});
taskBar = barBg.createDiv({ attr: { style: "height: 100%; width: 0%; background: #00ff88; box-shadow: 0 0 10px rgba(0,255,136,0.3); transition: width 0.6s ease;" }});
if (goalPct > 0) {
    barWrap.createDiv({ attr: { style: `position: absolute; left: ${goalPct}%; top: 16px; bottom: -4px; width: 2px; transform: translateX(-1px); background: rgba(255,255,255,0.85); border-radius: 1px;` }});
    barWrap.createDiv({ text: `GOAL ${goalPct.toFixed(0)}%`, attr: { style: `position: absolute; left: ${goalPct}%; top: 0; transform: translateX(-50%); font-size: 0.65em; font-weight: 700; letter-spacing: 0.5px; opacity: 0.6; white-space: nowrap;` }});
}

// --- HABITS ROW ---
const cardHabits = grid.createDiv({ cls: "zos-card span-12", attr: { style: "margin-top: 20px;" } });
const hHeader = cardHabits.createDiv({ cls: "zos-card-title", attr: { style: "justify-content: space-between;" } });
hHeader.createDiv({ text: "🧬 BIO-METRICS (WEEKLY)" });
const addBtn = hHeader.createDiv({ 
    text: "ADD HABIT +", 
    attr: { style: "font-size: 0.75em; opacity: 0.6; cursor: pointer; color: var(--zos-accent); font-weight: 800; background: rgba(var(--zos-accent-rgb), 0.1); padding: 5px 15px; border-radius: 20px; transition: all 0.3s ease;" }
});

const hGrid = cardHabits.createDiv({ attr: { style: "display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;" }});

function renderHabits() {
    hGrid.innerHTML = "";
    savedHabits.forEach((h, idx) => {
        const strip = hGrid.createDiv({ cls: "zos-habit-strip" });
        const nameEl = strip.createDiv({ text: h.toUpperCase(), cls: "zos-habit-title" });
        
        strip.oncontextmenu = (e) => {
            e.preventDefault();
            Utils.showModal({
                title: "Edit Habit",
                value: h,
                onSave: (newName) => {
                    savedHabits[idx] = newName;
                    localStorage.setItem("zos-final-habits", JSON.stringify(savedHabits));
                    renderHabits();
                    Utils.updateBars();
                },
                onDelete: () => {
                    savedHabits.splice(idx, 1);
                    localStorage.setItem("zos-final-habits", JSON.stringify(savedHabits));
                    renderHabits();
                    Utils.updateBars();
                }
            });
        };

        const dots = strip.createDiv({ cls: "zos-dot-grid" });
        for(let i=1; i<=7; i++) {
            const key = `zos-v28-h-${h}-${i}`;
            const dot = dots.createDiv({ cls: `zos-dot ${localStorage.getItem(key) ? 'active' : ''}` });
            dot.onclick = (ev) => {
                ev.stopPropagation();
                dot.classList.toggle('active');
                localStorage.getItem(key) ? localStorage.removeItem(key) : localStorage.setItem(key, '1');
                Utils.updateBars();
            };
        }
    });
}

addBtn.onclick = () => {
    Utils.showModal({
        title: "New Habit",
        placeholder: "E.g.: Read 30 min...",
        onSave: (name) => {
            savedHabits.push(name);
            localStorage.setItem("zos-final-habits", JSON.stringify(savedHabits));
            renderHabits();
            Utils.updateBars();
        }
    });
};

addBtn.onmouseenter = () => { addBtn.style.opacity = "1"; addBtn.style.transform = "translateY(-2px)"; };
addBtn.onmouseleave = () => { addBtn.style.opacity = "0.6"; addBtn.style.transform = "translateY(0)"; };

renderHabits();
Utils.updateBars();

// --- DISCOVERY ---
const discovery = container.createDiv({ cls: "span-12", attr: { style: "margin-top: 20px;" }});
const cardSeren = discovery.createDiv({ cls: "zos-card" });
const sHead = cardSeren.createDiv({ cls: "zos-card-title", attr: { style: "justify-content: space-between;" }});
sHead.createDiv({ text: "💡 SERENDIPITY" });
const ref = sHead.createDiv({ cls: "zos-refresh-icon", text: "↺" });

const sBody = cardSeren.createDiv({ attr: { style: "margin-top: 10px;" } });
function getRand() {
    sBody.innerHTML = "";
    const all = dv.pages().array();
    const r = all[Math.floor(Math.random() * all.length)];
    if(r) {
        const l = sBody.createDiv({ text: r.file.name, attr: { style: "font-family: var(--zos-font-ser); font-size: 2.2em; cursor: pointer; color: var(--zos-accent);" }});
        l.onclick = () => app.workspace.openLinkText(r.file.path, "", false);
    }
}

ref.onclick = (e) => { e.stopPropagation(); getRand(); new Notice("Syncing new idea..."); };
getRand();
```
