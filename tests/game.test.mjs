import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../TemplateData/game.js", import.meta.url), "utf8");

function setup({ loader = true, reject = false, throwSync = false, coarse = false, fullscreenThrows = false, pending = false } = {}) {
  const elements = new Map();
  const timers = [];
  const calls = [];
  let resolveLoad;
  let rejectLoad;
  function element() {
    return {
      dataset: {}, style: {}, attributes: {}, hidden: false, disabled: true,
      children: [], listeners: {},
      setAttribute(name, value) { this.attributes[name] = value; },
      appendChild(child) { this.children.push(child); child.parent = this; },
      get childElementCount() { return this.children.length; },
      remove() { this.parent.children = this.parent.children.filter((child) => child !== this); },
      addEventListener(name, callback) { this.listeners[name] = callback; },
    };
  }
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, element());
      return elements.get(selector);
    },
    createElement: element,
  };
  const context = {
    document,
    window: {
      matchMedia: () => ({ matches: coarse }),
      devicePixelRatio: 3,
      setTimeout: (callback) => timers.push(callback),
    },
  };
  if (loader) {
    context.createUnityInstance = (canvas, config, progress) => {
      calls.push({ canvas, config, progress });
      if (throwSync) throw new Error("sync failure");
      if (pending) return new Promise((resolve, reject) => {
        resolveLoad = resolve;
        rejectLoad = reject;
      });
      return reject ? Promise.reject("download failed") : Promise.resolve({
        SetFullscreen(value) {
          calls.push({ fullscreen: value });
          if (fullscreenThrows) throw new Error("not available");
        },
      });
    };
  }
  vm.runInNewContext(source, context);
  return { elements, timers, calls, resolveLoad, rejectLoad };
}

async function flush() { await new Promise((resolve) => setImmediate(resolve)); }

test("loads the unchanged Unity build, reports progress, and enables fullscreen", async () => {
  const { elements, calls } = setup();
  assert.equal(calls[0].config.codeUrl, "Build/simtactoc.wasm");
  assert.equal(calls[0].config.companyName, "DefaultCompany");
  assert.equal(calls[0].config.productName, "Sim Tac Toe");
  calls[0].progress(.54);
  assert.equal(elements.get("#unity-progress").attributes["aria-valuenow"], "54");
  calls[0].progress(1.1);
  assert.equal(elements.get("#unity-progress-bar-full").style.width, "100%");
  await flush();
  assert.equal(elements.get("#unity-container").dataset.state, "ready");
  assert.equal(elements.get("#unity-container").attributes["aria-busy"], "false");
  assert.equal(elements.get("#unity-loading-bar").hidden, true);
  assert.equal(elements.get("#unity-fullscreen-button").disabled, false);
  elements.get("#unity-fullscreen-button").listeners.click();
  assert.equal(calls.at(-1).fullscreen, 1);
});

for (const options of [{ loader: false }, { reject: true }, { throwSync: true }]) {
  test(`handles loader failure: ${JSON.stringify(options)}`, async () => {
    const { elements } = setup(options);
    await flush();
    assert.equal(elements.get("#unity-container").dataset.state, "error");
    assert.equal(elements.get("#unity-loading-bar").hidden, true);
    assert.equal(elements.get("#unity-fullscreen-button").disabled, true);
    assert.equal(elements.get("#unity-warning").hidden, false);
    assert.match(elements.get("#unity-warning").children[0].textContent, /Reload the page/);
  });
}

test("renders diagnostic text without interpreting HTML and removes temporary warnings", () => {
  const { calls, elements, timers } = setup();
  calls[0].config.showBanner("<img src=x onerror=alert(1)>", "warning");
  assert.equal(elements.get("#unity-warning").children[0].textContent, "<img src=x onerror=alert(1)>");
  timers[0]();
  assert.equal(elements.get("#unity-warning").hidden, true);
  calls[0].config.showBanner("persistent error", "error");
  assert.equal(timers.length, 1);
});

test("fatal banner exits loading while the loader promise remains pending", async () => {
  const { calls, elements, timers } = setup({ pending: true });
  const message = "<img src=x onerror=alert(1)>";
  calls[0].progress(.25);
  calls[0].config.showBanner(message, "error");
  assert.equal(elements.get("#unity-container").dataset.state, "error");
  assert.equal(elements.get("#unity-container").attributes["aria-busy"], "false");
  assert.equal(elements.get("#unity-loading-bar").hidden, true);
  assert.equal(elements.get("#unity-fullscreen-button").disabled, true);
  const banner = elements.get("#unity-warning");
  assert.equal(banner.hidden, false);
  assert.equal(banner.childElementCount, 1);
  assert.equal(banner.children[0].textContent,
    `The game could not start. ${message} Reload the page to try again.`);
  assert.equal(timers.length, 0);
  calls[0].progress(.9);
  await flush();
  assert.equal(elements.get("#unity-container").dataset.state, "error");
  assert.equal(elements.get("#unity-progress").attributes["aria-valuenow"], "25");
  assert.equal(elements.get("#unity-progress-bar-full").style.width, "25%");
});

test("late loader resolution cannot overwrite a fatal banner state", async () => {
  const { calls, elements, resolveLoad } = setup({ pending: true });
  calls[0].config.showBanner("fatal startup failure", "error");
  resolveLoad({ SetFullscreen() { assert.fail("fatal game must not enter fullscreen"); } });
  await flush();
  calls[0].progress(1);
  assert.equal(elements.get("#unity-container").dataset.state, "error");
  assert.equal(elements.get("#unity-container").attributes["aria-busy"], "false");
  assert.equal(elements.get("#unity-loading-bar").hidden, true);
  assert.equal(elements.get("#unity-fullscreen-button").disabled, true);
  assert.equal(elements.get("#unity-fullscreen-button").listeners.click, undefined);
  assert.equal(elements.get("#unity-progress").attributes["aria-valuenow"], undefined);
  assert.equal(elements.get("#unity-warning").childElementCount, 1);
});

test("fatal banners do not recurse or duplicate after repeated callbacks and rejection", async () => {
  const { calls, elements, rejectLoad, timers } = setup({ pending: true });
  assert.doesNotThrow(() => calls[0].config.showBanner("fatal startup failure", "error"));
  calls[0].config.showBanner("fatal startup failure", "error");
  rejectLoad("fatal startup failure");
  await flush();
  const banner = elements.get("#unity-warning");
  assert.equal(banner.childElementCount, 1);
  assert.equal(banner.children[0].textContent,
    "The game could not start. fatal startup failure Reload the page to try again.");
  assert.equal(elements.get("#unity-container").dataset.state, "error");
  assert.equal(timers.length, 0);
});

test("limits mobile render density without changing desktop density", () => {
  assert.equal(setup({ coarse: true }).calls[0].config.devicePixelRatio, 2);
  assert.equal(setup().calls[0].config.devicePixelRatio, undefined);
});

test("shows a nonfatal message when fullscreen throws", async () => {
  const { elements, timers } = setup({ fullscreenThrows: true });
  await flush();
  elements.get("#unity-fullscreen-button").listeners.click();
  assert.equal(elements.get("#unity-container").dataset.state, "ready");
  assert.match(elements.get("#unity-warning").children[0].textContent, /Fullscreen is unavailable/);
  assert.equal(timers.length, 1);
});
