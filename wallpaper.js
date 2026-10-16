// Space wallpapers, painted by code once (and again on resize), with a live star layer on top.
window.Wallpaper = (function () {
  "use strict";

  const bgCanvas = document.getElementById("wallpaper");
  const fgCanvas = document.getElementById("stars");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STAR_COLORS = ["#ffffff", "#ffffff", "#f1e9ff", "#d9ccff", "#ffe9f6", "#dfe6ff"];

  /* ---------- Seeded Perlin noise ---------- */

  function rng(seed) {
    return function () {
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeNoise(seed) {
    const rand = rng(seed);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      const t = p[i]; p[i] = p[j]; p[j] = t;
    }
    const perm = new Uint8Array(512);
    for (let i = 0; i < 512; i++) perm[i] = p[i & 255];
    const gx = [1, -1, 1, -1, 1, -1, 0, 0];
    const gy = [1, 1, -1, -1, 0, 0, 1, -1];

    function noise(x, y) {
      const xi = Math.floor(x), yi = Math.floor(y);
      const X = xi & 255, Y = yi & 255;
      const fx = x - xi, fy = y - yi;
      const u = fx * fx * fx * (fx * (fx * 6 - 15) + 10);
      const v = fy * fy * fy * (fy * (fy * 6 - 15) + 10);
      const a = perm[X] + Y, b = perm[X + 1] + Y;
      const h00 = perm[a] & 7, h01 = perm[a + 1] & 7, h10 = perm[b] & 7, h11 = perm[b + 1] & 7;
      const n00 = gx[h00] * fx + gy[h00] * fy;
      const n10 = gx[h10] * (fx - 1) + gy[h10] * fy;
      const n01 = gx[h01] * fx + gy[h01] * (fy - 1);
      const n11 = gx[h11] * (fx - 1) + gy[h11] * (fy - 1);
      const x0 = n00 + u * (n10 - n00), x1 = n01 + u * (n11 - n01);
      return x0 + v * (x1 - x0);
    }

    function fbm(x, y, octaves) {
      let sum = 0, amp = 0.5, f = 1;
      for (let i = 0; i < octaves; i++) {
        sum += amp * noise(x * f, y * f);
        f *= 2.02;
        amp *= 0.5;
      }
      return sum;
    }

    return { fbm };
  }

  const N = makeNoise(20261015);
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const mix = (a, b, t) => a + (b - a) * t;

  /* ---------- Scenes ---------- */

  const SCENES = {
    space: { bg: "#030208", nebula: { amount: 1, focus: [0.3, 0.3, 0.9], hue: 0 }, planet: "corner", dust: 1 },
    nebula: { bg: "#040209", nebula: { amount: 1.3, focus: null, hue: 0.05 }, dust: 1.25 },
    stars: { bg: "#020104", dust: 1.5 },
    dusk: { bg: "#030208", nebula: { amount: 0.55, focus: [0.55, 0.12, 0.85], hue: -0.15 }, planet: "horizon", dust: 0.85 },
    black: { bg: "#000000" }
  };

  function planetFor(kind, W, H) {
    const m = Math.max(W, H);
    if (kind === "corner") return { x: W - 0.07 * m, y: H + 0.03 * m, r: 0.22 * m };
    if (kind === "horizon") { const r = m * 1.3; return { x: W * 0.42, y: H * 0.76 + r, r }; }
    return null;
  }

  function offscreen(w, h) {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    return c;
  }

  function paintNebula(ctx, W, H, opt) {
    const m = Math.max(W, H);
    const scale = Math.min(1, 360 / m);
    const w = Math.max(8, Math.round(W * scale)), h = Math.max(8, Math.round(H * scale));
    const img = new ImageData(w, h), d = img.data;
    const f = 2.4 / Math.max(w, h);

    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const nx = x * f, ny = y * f;
        // Domain-warped noise gives the wispy, folded look of real gas clouds.
        const qx = N.fbm(nx + 3.1, ny + 7.7, 4), qy = N.fbm(nx + 11.2, ny + 1.4, 4);
        const n = N.fbm(nx * 1.3 + 2.2 * qx, ny * 1.3 + 2.2 * qy, 6);
        let dens = smooth(-0.12, 0.5, n);
        if (opt.focus) {
          const [fx, fy, fr] = opt.focus;
          const dist = Math.hypot((x / w - fx) * W / m, (y / h - fy) * H / m);
          dens *= 1 - smooth(fr * 0.2, fr, dist);
        }
        const lanes = N.fbm(nx * 3 + 50, ny * 3 + 20, 4);
        dens *= 1 - smooth(0.02, 0.4, lanes) * 0.8;
        dens = Math.min(1.4, dens * opt.amount);

        const t = smooth(-0.32, 0.32, N.fbm(nx * 0.8 + 70, ny * 0.8 + 30, 3) + opt.hue);
        let r, g, b;
        if (t < 0.5) { const k = t * 2; r = mix(52, 132, k); g = mix(50, 58, k); b = mix(185, 215, k); }
        else { const k = (t - 0.5) * 2; r = mix(132, 214, k); g = mix(58, 70, k); b = mix(215, 158, k); }
        const a = Math.min(1, dens * 0.8);
        const core = smooth(0.7, 1.4, dens) * 0.8;
        const i = (y * w + x) * 4;
        d[i] = Math.min(255, r * a + 255 * core * 0.5);
        d[i + 1] = Math.min(255, g * a + 205 * core * 0.42);
        d[i + 2] = Math.min(255, b * a + 255 * core * 0.5);
        d[i + 3] = 255;
      }
    }

    const off = offscreen(w, h);
    off.getContext("2d").putImageData(img, 0, 0);
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    if ("filter" in ctx) ctx.filter = `blur(${Math.max(0.5, 0.6 / scale).toFixed(1)}px)`;
    ctx.drawImage(off, 0, 0, W, H);
    ctx.restore();
  }

  function paintDust(ctx, W, H, amount) {
    const R = rng(77);
    const m = Math.max(W, H);
    const sf = Math.min(1.5, Math.max(0.35, m / 1920));
    const count = Math.round(Math.max(90, (W * H) / 1000) * amount);
    for (let i = 0; i < count; i++) {
      const x = R() * W, y = R() * H;
      const cluster = N.fbm((x / m) * 3 + 5, (y / m) * 3 + 9, 3);
      if (R() > 0.4 + cluster * 1.1) continue; // clumpier, like a real star field
      const pick = R();
      const s = (pick > 0.985 ? 1.6 : pick > 0.9 ? 1 : 0.6) * Math.max(0.7, sf);
      ctx.globalAlpha = 0.22 + R() * 0.6;
      ctx.fillStyle = STAR_COLORS[(R() * STAR_COLORS.length) | 0];
      ctx.fillRect(x, y, s, s);
    }

    // A few bright stars with soft halos and faint diffraction spikes.
    const bright = Math.round((W * H) / 140000 * amount) + 3;
    for (let i = 0; i < bright; i++) {
      const x = R() * W, y = R() * H * 0.8, r = (1 + R() * 1.1) * sf;
      const g = ctx.createRadialGradient(x, y, 0, x, y, r * 7);
      g.addColorStop(0, "rgba(255,255,255,0.95)");
      g.addColorStop(0.12, "rgba(230,215,255,0.4)");
      g.addColorStop(1, "rgba(200,170,255,0)");
      ctx.globalAlpha = 0.65 + R() * 0.35;
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, r * 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha *= 0.45;
      ctx.fillStyle = "rgba(235,225,255,0.7)";
      ctx.fillRect(x - r * 6, y - 0.35, r * 12, 0.7);
      ctx.fillRect(x - 0.35, y - r * 6, 0.7, r * 12);
    }
    ctx.globalAlpha = 1;
  }

  function paintPlanet(ctx, p) {
    const { x, y, r } = p;
    const glow = ctx.createRadialGradient(x, y, r * 0.96, x, y, r * 1.22);
    glow.addColorStop(0, "rgba(150, 105, 255, 0.5)");
    glow.addColorStop(0.22, "rgba(120, 80, 235, 0.16)");
    glow.addColorStop(1, "rgba(90, 50, 200, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, r * 1.22, 0, Math.PI * 2);
    ctx.fill();

    const S = Math.max(24, Math.min(420, Math.round(r)));
    const img = new ImageData(S, S), d = img.data;
    const L = [-0.88, -0.3, 0.38];
    const len = Math.hypot(L[0], L[1], L[2]);
    L[0] /= len; L[1] /= len; L[2] /= len;
    const ct = Math.cos(0.32), st = Math.sin(0.32);

    for (let j = 0; j < S; j++) {
      for (let i = 0; i < S; i++) {
        const k = (j * S + i) * 4;
        const px = ((i + 0.5) / S) * 2 - 1, py = ((j + 0.5) / S) * 2 - 1;
        const rr = px * px + py * py;
        if (rr > 1) { d[k + 3] = 0; continue; }
        const pz = Math.sqrt(1 - rr);
        const lat = py * ct + px * st;
        const lon = Math.atan2(px * ct - py * st, pz);
        const warp = N.fbm(lon * 1.5 + 20, lat * 4 + 5, 4);
        const band = Math.sin(lat * 9 + warp * 2.6) * 0.5 + 0.5;
        const fine = N.fbm(lon * 4 + 3, lat * 18 + 1, 3) * 0.5 + 0.5;
        const t = band * 0.7 + fine * 0.3;
        let sr = mix(24, 112, t), sg = mix(13, 80, t), sb = mix(58, 178, t);
        const storm = smooth(0.3, 0.55, N.fbm(lon * 3 + 40, lat * 6 + 40, 3));
        sr = mix(sr, 176, storm * 0.3);
        sg = mix(sg, 98, storm * 0.2);
        sb = mix(sb, 178, storm * 0.25);
        const lambert = px * L[0] + py * L[1] + pz * L[2];
        const shade = 0.03 + 0.97 * Math.pow(smooth(-0.2, 0.75, lambert), 1.3);
        const rim = Math.pow(1 - pz, 4) * smooth(-0.2, 0.5, lambert) * 0.55;
        d[k] = Math.min(255, sr * shade + 150 * rim);
        d[k + 1] = Math.min(255, sg * shade + 112 * rim);
        d[k + 2] = Math.min(255, sb * shade + 235 * rim);
        d[k + 3] = 255;
      }
    }

    const off = offscreen(S, S);
    off.getContext("2d").putImageData(img, 0, 0);
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.clip();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(off, x - r, y - r, r * 2, r * 2);
    ctx.restore();
  }

  function paintSky(ctx, W, H, p) {
    const top = Math.min(0.98, Math.max(0.1, (p.y - p.r) / H));
    const sky = ctx.createLinearGradient(0, 0, 0, H);
    sky.addColorStop(0, "#030208");
    sky.addColorStop(top * 0.6, "#0a0516");
    sky.addColorStop(top, "#22104a");
    sky.addColorStop(1, "#160a2e");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, H);
  }

  function paintHorizon(ctx, p, W, H) {
    const { x, y, r } = p;
    const glow = ctx.createRadialGradient(x, y, r * 0.985, x, y, r * 1.08);
    glow.addColorStop(0, "rgba(205, 165, 255, 0.85)");
    glow.addColorStop(0.07, "rgba(160, 110, 255, 0.42)");
    glow.addColorStop(0.4, "rgba(110, 60, 220, 0.1)");
    glow.addColorStop(1, "rgba(80, 40, 180, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, r * 1.08, 0, Math.PI * 2);
    ctx.fill();

    const body = ctx.createLinearGradient(0, y - r, 0, y - r + H * 0.3);
    body.addColorStop(0, "#2a1650");
    body.addColorStop(0.05, "#140a28");
    body.addColorStop(1, "#040208");
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "rgba(230, 205, 255, 0.6)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.stroke();

    // Sunrise peeking over the limb, with a wide horizontal flare.
    const sx = W * 0.7;
    const sy = y - Math.sqrt(Math.max(0, r * r - (sx - x) * (sx - x)));
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    const sun = ctx.createRadialGradient(sx, sy, 0, sx, sy, Math.max(W, H) * 0.35);
    sun.addColorStop(0, "rgba(255, 240, 255, 0.95)");
    sun.addColorStop(0.025, "rgba(235, 195, 255, 0.55)");
    sun.addColorStop(0.18, "rgba(170, 110, 255, 0.16)");
    sun.addColorStop(1, "rgba(120, 60, 220, 0)");
    ctx.fillStyle = sun;
    ctx.fillRect(0, 0, W, H);
    ctx.translate(sx, sy);
    ctx.scale(1, 0.05);
    const streak = ctx.createRadialGradient(0, 0, 0, 0, 0, W * 0.55);
    streak.addColorStop(0, "rgba(240, 215, 255, 0.55)");
    streak.addColorStop(1, "rgba(160, 100, 255, 0)");
    ctx.fillStyle = streak;
    ctx.beginPath();
    ctx.arc(0, 0, W * 0.55, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // Paints a full scene onto a canvas and returns the planet (stars behind it get hidden).
  function paint(canvas, id, W, H, dpr) {
    const scene = SCENES[id] || SCENES.space;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = scene.bg;
    ctx.fillRect(0, 0, W, H);
    const planet = planetFor(scene.planet, W, H);
    if (scene.planet === "horizon") paintSky(ctx, W, H, planet);
    if (scene.nebula) paintNebula(ctx, W, H, scene.nebula);
    if (scene.dust) paintDust(ctx, W, H, scene.dust);
    if (planet) {
      if (scene.planet === "horizon") paintHorizon(ctx, planet, W, H);
      else paintPlanet(ctx, planet);
    }
    return planet;
  }

  /* ---------- Live star layer ---------- */

  let W = 0, H = 0, dpr = 1, scene = "space", planet = null, paintedKey = "";
  let stars = [], meteor = null, running = false, last = 0, moving = true, meteorsOn = true;
  const fg = fgCanvas.getContext("2d");

  function seedStars() {
    const R = rng(4242);
    const count = Math.round((W * H) / 5200);
    stars = Array.from({ length: count }, () => {
      const depth = R();
      return {
        x: R() * W, y: R() * H, r: 0.45 + depth * depth * 1.3, a: 0.4 + R() * 0.6,
        speed: 0.01 + depth * 0.035, tw: 0.0006 + R() * 0.0018, ph: R() * Math.PI * 2,
        c: STAR_COLORS[(R() * STAR_COLORS.length) | 0]
      };
    });
  }

  function drawStars(t, advance) {
    fg.setTransform(dpr, 0, 0, dpr, 0, 0);
    fg.clearRect(0, 0, W, H);
    if (scene === "black") return;
    for (const s of stars) {
      if (advance) { s.x -= s.speed; if (s.x < -3) s.x = W + 3; }
      if (planet && (s.x - planet.x) ** 2 + (s.y - planet.y) ** 2 < planet.r * planet.r) continue;
      fg.globalAlpha = s.a * (0.6 + 0.4 * Math.sin(t * s.tw + s.ph));
      fg.fillStyle = s.c;
      fg.beginPath();
      fg.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      fg.fill();
      if (s.r > 1.25) {
        fg.globalAlpha *= 0.15;
        fg.beginPath();
        fg.arc(s.x, s.y, s.r * 4, 0, Math.PI * 2);
        fg.fill();
      }
    }
    if (advance && meteorsOn) {
      if (!meteor && Math.random() < 0.003) {
        meteor = { x: W * (0.3 + Math.random() * 0.7), y: H * Math.random() * 0.35, vx: -(9 + Math.random() * 6), vy: 4 + Math.random() * 3, life: 1 };
      }
      if (meteor) {
        const m = meteor, tx = m.x - m.vx * 12, ty = m.y - m.vy * 12;
        const g = fg.createLinearGradient(m.x, m.y, tx, ty);
        g.addColorStop(0, "rgba(255,255,255,0.95)");
        g.addColorStop(1, "rgba(200,160,255,0)");
        fg.globalAlpha = m.life;
        fg.strokeStyle = g;
        fg.lineWidth = 1.5;
        fg.lineCap = "round";
        fg.beginPath();
        fg.moveTo(m.x, m.y);
        fg.lineTo(tx, ty);
        fg.stroke();
        m.x += m.vx;
        m.y += m.vy;
        m.life -= 0.025;
        if (m.life <= 0) meteor = null;
      }
    }
    fg.globalAlpha = 1;
  }

  function loop(t) {
    if (!running) return;
    requestAnimationFrame(loop);
    if (t - last < 33) return; // ~30fps is plenty for drifting stars
    last = t;
    drawStars(t, true);
  }

  function repaint() {
    const nW = innerWidth, nH = innerHeight, nD = Math.min(window.devicePixelRatio || 1, 2);
    const key = `${scene}:${nW}x${nH}@${nD}`;
    if (key === paintedKey) return;
    paintedKey = key;
    W = nW; H = nH; dpr = nD;
    planet = paint(bgCanvas, scene, W, H, dpr);
    fgCanvas.width = Math.round(W * dpr);
    fgCanvas.height = Math.round(H * dpr);
    seedStars();
    if (!running) drawStars(0, false);
  }

  function updateLoop() {
    const run = moving && !reduced && scene !== "black";
    if (run && !running) {
      running = true;
      requestAnimationFrame(loop);
    } else if (!run) {
      running = false;
      drawStars(0, false);
    }
  }

  let resizeTimer = 0;
  addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(repaint, 180);
  });

  const thumbs = new Map();

  return {
    set(opts) {
      scene = SCENES[opts.wallpaper] ? opts.wallpaper : "space";
      moving = !!opts.moving;
      meteorsOn = !!opts.meteors;
      if (!meteorsOn) meteor = null;
      repaint();
      updateLoop();
    },
    // A small JPEG of a scene, for previews and the browser's new tab page.
    thumbURL(id, w, h) {
      const key = `${id}:${w}x${h}`;
      if (!thumbs.has(key)) {
        const c = offscreen(w, h);
        paint(c, id, w, h, 1);
        thumbs.set(key, c.toDataURL("image/jpeg", 0.88));
      }
      return thumbs.get(key);
    }
  };
})();
