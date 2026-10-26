/* The Unity build stays untouched; this file controls its page wrapper. */
(() => {
  "use strict";

  const container = document.querySelector("#unity-container");
  const canvas = document.querySelector("#unity-canvas");
  const loadingBar = document.querySelector("#unity-loading-bar");
  const progressBar = document.querySelector("#unity-progress");
  const progressFill = document.querySelector("#unity-progress-bar-full");
  const fullscreenButton = document.querySelector("#unity-fullscreen-button");
  const warningBanner = document.querySelector("#unity-warning");
  let hasFatalError = false;

  function showBanner(message, type) {
    if (type === "error") {
      fail(message);
      return;
    }
    renderBanner(message, type);
  }

  function renderBanner(message, type) {
    const paragraph = document.createElement("p");
    paragraph.textContent = String(message);
    warningBanner.appendChild(paragraph);
    warningBanner.hidden = false;
    if (type !== "error") {
      window.setTimeout(() => {
        paragraph.remove();
        warningBanner.hidden = !warningBanner.childElementCount;
      }, 5000);
    }
  }

  function fail(message) {
    if (hasFatalError) return;
    hasFatalError = true;
    container.dataset.state = "error";
    container.setAttribute("aria-busy", "false");
    loadingBar.hidden = true;
    fullscreenButton.disabled = true;
    renderBanner(`The game could not start. ${String(message)} Reload the page to try again.`, "error");
  }

  if (typeof createUnityInstance !== "function") {
    fail("The game loader did not download. Check your connection.");
    return;
  }

  const config = {
    dataUrl: "Build/simtactoc.data",
    frameworkUrl: "Build/simtactoc.framework.js",
    codeUrl: "Build/simtactoc.wasm",
    streamingAssetsUrl: "StreamingAssets",
    companyName: "DefaultCompany",
    productName: "Sim Tac Toe",
    productVersion: "0.1.0",
    showBanner,
  };

  // Keep browser-sized mobile displays from allocating a large HiDPI render target.
  if (window.matchMedia("(pointer: coarse)").matches) {
    config.devicePixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  }

  try {
    createUnityInstance(canvas, config, (progress) => {
      if (hasFatalError) return;
      const percentage = Math.round(Math.min(1, Math.max(0, progress)) * 100);
      progressFill.style.width = `${percentage}%`;
      progressBar.setAttribute("aria-valuenow", String(percentage));
    }).then((instance) => {
      if (hasFatalError) return;
      loadingBar.hidden = true;
      container.dataset.state = "ready";
      container.setAttribute("aria-busy", "false");
      fullscreenButton.disabled = false;
      fullscreenButton.addEventListener("click", () => {
        try {
          instance.SetFullscreen(1);
        } catch {
          showBanner("Fullscreen is unavailable in this browser. You can still play here.", "warning");
        }
      });
    }).catch(fail);
  } catch (error) {
    fail(error);
  }
})();
