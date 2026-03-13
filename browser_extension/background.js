let activeTabData = { id: null, domain: null, url: null };
let startTime = Date.now();

// Set up repeating alarm correctly for Manifest V3 (minimum 1 minute typically, 
// but for this demo using 0.5 can still run once a minute locally, 
// or setInterval as fallback in local unpacked extension mode).
chrome.alarms.create("syncLoop", { periodInMinutes: 0.5 }); 

// Keep track of active tab when tab is activated (switched)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  await logCurrentTab();
  await updateActiveTab(activeInfo.tabId);
});

// Keep track of tab update (e.g., navigated to new URL)
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (tabId === activeTabData.id && changeInfo.url) {
    await logCurrentTab();
    await updateActiveTab(tabId);
  }
});

// Handle window focus changes
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    // Window lost focus, flush time, set active tab to null
    await logCurrentTab();
    activeTabData = { id: null, domain: null, url: null };
  } else {
    // Window gained focus, get the active tab
    const tabs = await chrome.tabs.query({ active: true, windowId: windowId });
    if (tabs.length > 0) {
      await logCurrentTab();
      await updateActiveTab(tabs[0].id);
    }
  }
});

// Periodic background sync
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "syncLoop") {
    // Every 30s flush current elapsed time to backend and restart timer
    await logCurrentTab(); 
  }
});

async function updateActiveTab(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (tab && tab.url && (tab.url.startsWith('http://') || tab.url.startsWith('https://'))) {
      const urlObj = new URL(tab.url);
      activeTabData = {
        id: tabId,
        domain: urlObj.hostname,
        url: tab.url
      };
    } else {
      activeTabData = { id: tabId, domain: null, url: null };
    }
  } catch (e) {
    activeTabData = { id: null, domain: null, url: null };
  }
  startTime = Date.now();
}

async function logCurrentTab() {
  if (activeTabData.domain && startTime) {
    const endTime = Date.now();
    const durationSeconds = Math.floor((endTime - startTime) / 1000);
    
    if (durationSeconds > 0) {
      await sendToBackend(activeTabData.domain, activeTabData.url, durationSeconds);
    }
  }
  // Reset the start time so we don't double count the same duration
  startTime = Date.now();
}

async function sendToBackend(domain, url, durationSeconds) {
  try {
    await fetch("http://localhost:5000/api/tracker/browser", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        domain: domain,
        url: url || "",
        duration_seconds: durationSeconds
      })
    });
  } catch (err) {
    console.warn("Backend not reachable / tracker error:", err);
  }
}
