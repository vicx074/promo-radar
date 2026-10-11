import {describe, expect, it} from "vitest";
import {formatBrl, safeProductImage} from "./format";

describe("utils", () => {
  it("formats integer cents without float values in data", () => {
    expect(formatBrl(19990)).toContain("199,90");
  });
  it("only renders image URLs from the allowed ML CDN", () => {
    expect(safeProductImage("https://http2.mlstatic.com/D_TEST.jpg")).toContain("mlstatic.com");
    expect(safeProductImage("https://evil.example/a.jpg")).toBe(null);
    expect(safeProductImage("javascript:alert(1)")).toBe(null);
    expect(safeProductImage("https://http2.mlstatic.com.evil.example/a.jpg")).toBe(null);
    expect(safeProductImage(null)).toBe(null);
  });
});
