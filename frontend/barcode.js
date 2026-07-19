/* Pure-JS EAN-13 / EAN-8 / UPC-A decoder.
 *
 * Why this exists: the browser BarcodeDetector API is Chrome-only. Firefox,
 * Safari (so every iPad) and many Chrome desktop builds do not have it, and the
 * app previously dead-ended on "Ce navigateur ne sait pas décoder les
 * codes-barres." A shop-floor tablet app cannot depend on one browser engine.
 *
 * Why it is vendored rather than pulled from a CDN: BatchTwin deploys
 * on-premise, behind a plant firewall, and is a PWA expected to work offline.
 * A CDN dependency would fail exactly where the product is used.
 *
 * Scope, stated honestly: 1D retail symbologies only (EAN-13, EAN-8, UPC-A) --
 * the formats a product label actually carries. QR is NOT decoded here; hand
 * rolling Reed-Solomon error correction would be disproportionate, and the
 * shop floor uses keyboard-wedge scanners for station QR anyway.
 *
 * The decoding functions are pure and take plain arrays, so they are tested
 * headlessly in tests/test_barcode.js against synthesised bitmaps.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.BTBarcode = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Digit patterns as the widths of four alternating runs, in modules.
  // L-code for a left digit (starts with a space); the same widths serve as the
  // R-code for a right digit (starts with a bar), because R is L complemented.
  const L = [
    [3, 2, 1, 1], [2, 2, 2, 1], [2, 1, 2, 2], [1, 4, 1, 1], [1, 1, 3, 2],
    [1, 2, 3, 1], [1, 1, 1, 4], [1, 3, 1, 2], [1, 2, 1, 3], [3, 1, 1, 2],
  ];
  // G-code (even parity) is the L pattern read backwards.
  const G = L.map(p => p.slice().reverse());

  // Which of the first six digits are G-coded encodes the 13th digit.
  const PARITY = ["000000", "001011", "001101", "001110", "010011",
                  "011001", "011100", "010101", "010110", "011010"];

  const DIGIT_MODULES = 7;
  const MAX_INDIVIDUAL_VARIANCE = 0.7;   // per-run tolerance, in modules
  const MAX_AVG_VARIANCE = 0.48;         // reject a digit that fits this badly

  /* ---------------------------------------------------------------- matching */

  function patternVariance(counters, pattern) {
    let total = 0, patternTotal = 0;
    for (let i = 0; i < counters.length; i++) {
      total += counters[i];
      patternTotal += pattern[i];
    }
    if (total < patternTotal) return Infinity;   // fewer pixels than modules
    const unit = total / patternTotal;
    const maxVar = unit * MAX_INDIVIDUAL_VARIANCE;
    let variance = 0;
    for (let i = 0; i < counters.length; i++) {
      const d = Math.abs(counters[i] - pattern[i] * unit);
      if (d > maxVar) return Infinity;
      variance += d;
    }
    return variance / total;
  }

  /** Best-matching digit for four run widths. Returns null if nothing fits. */
  function bestDigit(counters, patterns) {
    let best = Infinity, digit = -1;
    for (let d = 0; d < 10; d++) {
      const v = patternVariance(counters, patterns[d]);
      if (v < best) { best = v; digit = d; }
    }
    return best <= MAX_AVG_VARIANCE ? { digit, variance: best } : null;
  }

  /* ------------------------------------------------------------------- runs */

  /**
   * Run-length encode a binarised scanline.
   * @param {Uint8Array|Array} bits 1 = dark, 0 = light
   * @returns {{len:number, dark:boolean}[]}
   */
  function toRuns(bits) {
    const runs = [];
    if (!bits.length) return runs;
    let cur = bits[0], len = 1;
    for (let i = 1; i < bits.length; i++) {
      if (bits[i] === cur) { len++; continue; }
      runs.push({ len, dark: cur === 1 });
      cur = bits[i]; len = 1;
    }
    runs.push({ len, dark: cur === 1 });
    return runs;
  }

  function widths(runs, from, n) {
    const out = new Array(n);
    for (let i = 0; i < n; i++) out[i] = runs[from + i].len;
    return out;
  }

  /* --------------------------------------------------------------- checksums */

  function checkDigit(digits) {
    // EAN-13 weights 1,3 from the left; EAN-8 weights 3,1. Both reduce to
    // "weight 3 on every second digit counting back from the check digit".
    let sum = 0;
    for (let i = 0; i < digits.length; i++) {
      const fromRight = digits.length - 1 - i;   // 0 = last data digit
      sum += digits[i] * (fromRight % 2 === 0 ? 3 : 1);
    }
    return (10 - (sum % 10)) % 10;
  }

  /** True if a full code (data digits + trailing check digit) is self-consistent. */
  function checksumOk(code) {
    if (!/^\d{8}$|^\d{12}$|^\d{13}$/.test(code)) return false;
    const digits = code.split("").map(Number);
    const check = digits.pop();
    return checkDigit(digits) === check;
  }

  /* ---------------------------------------------------------------- EAN-13 */

  // Run layout from the start guard: 3 guard + 24 left + 5 middle + 24 right + 3 end
  const EAN13_RUNS = 59;
  const EAN8_RUNS = 43;   // 3 + 16 + 5 + 16 + 3

  function guardLooksRight(runs, i) {
    // Start guard is bar,space,bar of one module each.
    if (!runs[i].dark) return false;
    const a = runs[i].len, b = runs[i + 1].len, c = runs[i + 2].len;
    const avg = (a + b + c) / 3;
    if (avg < 1) return false;
    return Math.abs(a - avg) <= avg * 0.6 &&
           Math.abs(b - avg) <= avg * 0.6 &&
           Math.abs(c - avg) <= avg * 0.6;
  }

  function decodeEan13(runs, i) {
    const left = [], parity = [];
    let p = i + 3;
    for (let d = 0; d < 6; d++, p += 4) {
      const c = widths(runs, p, 4);
      const odd = bestDigit(c, L);
      const even = bestDigit(c, G);
      if (!odd && !even) return null;
      if (odd && (!even || odd.variance <= even.variance)) {
        left.push(odd.digit); parity.push("0");
      } else {
        left.push(even.digit); parity.push("1");
      }
    }
    const first = PARITY.indexOf(parity.join(""));
    if (first < 0) return null;

    p = i + 32;   // skip the 5-run middle guard
    const right = [];
    for (let d = 0; d < 6; d++, p += 4) {
      const hit = bestDigit(widths(runs, p, 4), L);
      if (!hit) return null;
      right.push(hit.digit);
    }
    return String(first) + left.join("") + right.join("");
  }

  function decodeEan8(runs, i) {
    const left = [];
    let p = i + 3;
    for (let d = 0; d < 4; d++, p += 4) {
      const hit = bestDigit(widths(runs, p, 4), L);
      if (!hit) return null;
      left.push(hit.digit);
    }
    p = i + 24;   // 3 guard + 16 left + 5 middle
    const right = [];
    for (let d = 0; d < 4; d++, p += 4) {
      const hit = bestDigit(widths(runs, p, 4), L);
      if (!hit) return null;
      right.push(hit.digit);
    }
    return left.join("") + right.join("");
  }

  /**
   * Decode from run lengths. Tries every plausible start, and tries the line
   * backwards too, because a barcode presented upside down is the single most
   * common operator error.
   */
  function decodeRuns(runs) {
    for (const seq of [runs, reversedRuns(runs)]) {
      for (let i = 0; i + EAN8_RUNS <= seq.length; i++) {
        if (!guardLooksRight(seq, i)) continue;
        if (i + EAN13_RUNS <= seq.length) {
          const c = decodeEan13(seq, i);
          if (c && checksumOk(c)) return c;
        }
        const c8 = decodeEan8(seq, i);
        if (c8 && checksumOk(c8)) return c8;
      }
    }
    return null;
  }

  function reversedRuns(runs) {
    return runs.slice().reverse();
  }

  /* ------------------------------------------------------------ binarisation */

  /**
   * Decode one scanline of luminance values (0..255, higher = lighter).
   * Uses a midpoint threshold on that line only, so uneven lighting across the
   * frame does not sink a line that is locally fine.
   */
  function decodeLuma(luma) {
    let min = 255, max = 0;
    for (let i = 0; i < luma.length; i++) {
      if (luma[i] < min) min = luma[i];
      if (luma[i] > max) max = luma[i];
    }
    if (max - min < 40) return null;      // no real contrast: not a barcode
    const t = (min + max) / 2;
    const bits = new Uint8Array(luma.length);
    for (let i = 0; i < luma.length; i++) bits[i] = luma[i] < t ? 1 : 0;
    return decodeRuns(toRuns(bits));
  }

  /* ---------------------------------------------------------------- browser */

  /**
   * Try to read a barcode from a video frame.
   * Samples horizontal lines across the middle band, because that is where a
   * barcode sits when someone points a tablet at a box.
   */
  function decodeImageData(img, lines) {
    const { data, width, height } = img;
    const n = lines || 21;
    const luma = new Uint8Array(width);
    for (let k = 0; k < n; k++) {
      // spread the sampled rows over the middle 80% of the frame
      const y = Math.floor(height * (0.1 + 0.8 * (k + 0.5) / n));
      let o = y * width * 4;
      for (let x = 0; x < width; x++, o += 4) {
        // Rec. 601 luma, integer weights
        luma[x] = (data[o] * 77 + data[o + 1] * 150 + data[o + 2] * 29) >> 8;
      }
      const code = decodeLuma(luma);
      if (code) return code;
    }
    return null;
  }

  return {
    decodeRuns, decodeLuma, decodeImageData, toRuns, checksumOk, checkDigit,
    supported: true,
  };
});
