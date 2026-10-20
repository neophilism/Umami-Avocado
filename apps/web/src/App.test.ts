import { describe, expect, it } from "vitest";
import { researchPrograms } from "./App";
describe("research programs", () => { it("keeps yeast and avocado distinct", () => { expect(researchPrograms).toHaveLength(3); expect(researchPrograms[2]).toContain("Avocado"); }); });
