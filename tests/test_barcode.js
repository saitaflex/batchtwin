/* Headless tests for the vendored EAN decoder.
 *
 *   node tests/test_barcode.js
 *
 * Barcodes are synthesised from the spec (not captured), so the test proves the
 * decoder against the standard rather than against one lucky photograph. Noise,
 * blur, low contrast and upside-down presentation are exercised deliberately,
 * because that is what a tablet camera on a shop floor actually produces.
 */
"use strict";
const assert = require("assert");
const BC = require("../frontend/barcode.js");

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log("  ok   " + name); }
  catch (e) { failed++; console.log("  FAIL " + name + "\n       " + e.message); }
}

/* ------------------------------------------------------------ encoding side */
// Independent encoder, written from the spec, so a bug would have to appear
// identically in both directions to go unnoticed.
const L = ["0001101", "0011001", "0010011", "0111101", "0100011",
           "0110001", "0101111", "0111011", "0110111", "0001011"];
// R is L complemented; G is R *reversed* (not L reversed -- getting this wrong
// is why the first run of this test failed against a correct decoder).
const R = L.map(s => s.split("").map(c => (c === "0" ? "1" : "0")).join(""));
const G = R.map(s => s.split("").reverse().join(""));
const PARITY = ["000000", "001011", "001101", "001110", "010011",
                "011001", "011100", "010101", "010110", "011010"];

function encodeEan13(code) {
  assert.strictEqual(code.length, 13, "EAN-13 needs 13 digits");
  const d = code.split("").map(Number);
  const par = PARITY[d[0]];
  let s = "101";
  for (let i = 1; i <= 6; i++) s += (par[i - 1] === "0" ? L : G)[d[i]];
  s += "01010";
  for (let i = 7; i <= 12; i++) s += R[d[i]];
  return s + "101";
}

function encodeEan8(code) {
  assert.strictEqual(code.length, 8, "EAN-8 needs 8 digits");
  const d = code.split("").map(Number);
  let s = "101";
  for (let i = 0; i < 4; i++) s += L[d[i]];
  s += "01010";
  for (let i = 4; i < 8; i++) s += R[d[i]];
  return s + "101";
}

/** Render a module string to a luminance scanline. */
function toLuma(modules, {scale = 3, quiet = 12, dark = 30, light = 225} = {}) {
  const px = [];
  for (let i = 0; i < quiet * scale; i++) px.push(light);
  for (const m of modules) {
    for (let i = 0; i < scale; i++) px.push(m === "1" ? dark : light);
  }
  for (let i = 0; i < quiet * scale; i++) px.push(light);
  return Uint8Array.from(px);
}

function blur(luma, radius) {
  const out = new Uint8Array(luma.length);
  for (let i = 0; i < luma.length; i++) {
    let sum = 0, n = 0;
    for (let k = -radius; k <= radius; k++) {
      const j = i + k;
      if (j >= 0 && j < luma.length) { sum += luma[j]; n++; }
    }
    out[i] = Math.round(sum / n);
  }
  return out;
}

function noisy(luma, amp, seed) {
  // deterministic pseudo-random, so a failure is always reproducible
  let s = seed || 1;
  const rnd = () => (s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const out = new Uint8Array(luma.length);
  for (let i = 0; i < luma.length; i++) {
    out[i] = Math.max(0, Math.min(255, Math.round(luma[i] + (rnd() - 0.5) * 2 * amp)));
  }
  return out;
}

/* ------------------------------------------------------------------- checks */
console.log("\nchecksum");

test("known-good EAN-13 validates", () => {
  assert.ok(BC.checksumOk("4006381333931"));
});
test("known-good EAN-8 validates", () => {
  assert.ok(BC.checksumOk("96385074"));
});
test("a corrupted check digit is rejected", () => {
  assert.ok(!BC.checksumOk("4006381333932"));
});
test("check digit is computed correctly", () => {
  assert.strictEqual(BC.checkDigit("400638133393".split("").map(Number)), 1);
});

console.log("\ndecoding, clean signal");

const SAMPLES = ["4006381333931", "9780201379624", "5901234123457", "0012345678905"];

for (const code of SAMPLES) {
  test(`EAN-13 ${code} round-trips`, () => {
    assert.strictEqual(BC.decodeLuma(toLuma(encodeEan13(code))), code);
  });
}

test("EAN-8 96385074 round-trips", () => {
  assert.strictEqual(BC.decodeLuma(toLuma(encodeEan8("96385074"))), "96385074");
});

console.log("\ndecoding, realistic camera conditions");

test("upside down still decodes", () => {
  const luma = toLuma(encodeEan13("4006381333931"));
  const flipped = Uint8Array.from(Array.from(luma).reverse());
  assert.strictEqual(BC.decodeLuma(flipped), "4006381333931");
});

test("held close (scale 6) decodes", () => {
  assert.strictEqual(
    BC.decodeLuma(toLuma(encodeEan13("5901234123457"), {scale: 6})), "5901234123457");
});

test("held far (scale 2) decodes", () => {
  assert.strictEqual(
    BC.decodeLuma(toLuma(encodeEan13("5901234123457"), {scale: 2})), "5901234123457");
});

test("slightly out of focus decodes", () => {
  const luma = blur(toLuma(encodeEan13("4006381333931"), {scale: 4}), 2);
  assert.strictEqual(BC.decodeLuma(luma), "4006381333931");
});

test("sensor noise decodes", () => {
  const luma = noisy(toLuma(encodeEan13("9780201379624"), {scale: 4}), 22, 7);
  assert.strictEqual(BC.decodeLuma(luma), "9780201379624");
});

test("poor lighting (low contrast) decodes", () => {
  const luma = toLuma(encodeEan13("4006381333931"), {scale: 4, dark: 95, light: 165});
  assert.strictEqual(BC.decodeLuma(luma), "4006381333931");
});

test("barcode off-centre with wide margins decodes", () => {
  assert.strictEqual(
    BC.decodeLuma(toLuma(encodeEan13("4006381333931"), {quiet: 60})), "4006381333931");
});

console.log("\nrefusing to guess");

test("blank frame returns null, not a wrong code", () => {
  assert.strictEqual(BC.decodeLuma(new Uint8Array(600).fill(210)), null);
});

test("random texture returns null", () => {
  const junk = noisy(new Uint8Array(900).fill(128), 120, 3);
  assert.strictEqual(BC.decodeLuma(junk), null);
});

test("a barcode with a damaged bar is rejected rather than misread", () => {
  const mod = encodeEan13("4006381333931").split("");
  for (let i = 40; i < 47; i++) mod[i] = mod[i] === "1" ? "0" : "1";  // wreck one digit
  const got = BC.decodeLuma(toLuma(mod.join("")));
  assert.ok(got === null || got === "4006381333931",
            "misread a damaged symbol as " + got);
});

console.log("\nframe sampling");

test("decodeImageData finds a barcode in a 2D frame", () => {
  const modules = encodeEan13("5901234123457");
  const line = toLuma(modules, {scale: 3});
  const width = line.length, height = 60;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // bars only occupy the middle band; top and bottom are background
      const v = (y > 12 && y < 48) ? line[x] : 235;
      const o = (y * width + x) * 4;
      data[o] = data[o + 1] = data[o + 2] = v; data[o + 3] = 255;
    }
  }
  assert.strictEqual(BC.decodeImageData({data, width, height}), "5901234123457");
});

console.log(`\n${passed} passed, ${failed} failed\n`);
process.exit(failed ? 1 : 0);
