// background.js

chrome.browserAction.onClicked.addListener(function(tab) {
    chrome.tabs.create({ url: "http://localhost:5000" }); // Replace 5000 with your Flask app's port number
});

