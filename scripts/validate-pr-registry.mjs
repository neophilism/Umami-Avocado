import fs from "node:fs";
const path = new URL("../registry/prs.json", import.meta.url);
const p = JSON.parse(fs.readFileSync(path, "utf8"));
const fail = (msg) => { throw new Error("Invalid PR registry: " + msg); };
if (p.schemaVersion !== 1 || p.repository !== "neophilism/Umami-Avocado" || !Number.isSafeInteger(p.roadmapVersion) || p.roadmapVersion < 1 || !p.planVerified || !Array.isArray(p.units) || p.units.length !== 30 || p.plannedPrCount !== p.units.length || !Array.isArray(p.pullRequests) || !Number.isFinite(Date.parse(p.observedAt))) fail("envelope");
const ids = new Set();
for (const u of p.units) {
 if (!/^UA-[0-9]{3}$/.test(u.id) || ids.has(u.id) || !u.title || !Array.isArray(u.prs) || !Array.isArray(u.dependsOn) || !u.dependsOn.every(d => ids.has(d)) || !Array.isArray(u.acceptance) || !Array.isArray(u.externalPrerequisites)) fail("unit "+u.id);
 if (u.prs.some(n => !Number.isSafeInteger(n) || n <= 0)) fail("PR number for "+u.id);
 ids.add(u.id);
}
for (const r of p.pullRequests) if (!Number.isInteger(r.number) || !p.units.some(u=>u.prs.includes(r.number))) fail("orphan observed PR");
console.log("Registry valid: 30 units and acyclic ordered dependencies.");
