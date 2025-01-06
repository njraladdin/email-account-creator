const { plugin } = require('puppeteer-with-fingerprints');
const fs = require("fs");
const config = {
    ADD_RECOVERY_EMAIL: true,
    USE_PROXY: false,
    PROXY_USERNAME: 'username',
    PROXY_PASSWORD: 'password',
    PROXY_IP: 'ip',
    PROXY_PORT: 'port',
    NAMES_FILE: 'Utils/names.txt',
    WORDS_FILE: 'Utils/words5char.txt',
    ACCOUNTS_FILE: 'accounts.txt',
  };
  function log(message) {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ${message}`);
  }
  
  const recMail = require('./utils/temporary_email_creator');

async function start() {
  console.clear();

  log("Starting...", "green");

  log("Fetching Fingerprint...", "yellow");
  plugin.setServiceKey('');
  const fingerprint = await plugin.fetch({
    tags: ['Microsoft Windows', 'Chrome'],
  });

  log("Applying Fingerprint...", "yellow");
  plugin.useFingerprint(fingerprint);

  log("Fingerprint fetched and applied", "green");

  if (config.USE_PROXY) {
    log("Applying proxy settings...", "green");
    plugin.useProxy(`${config.PROXY_USERNAME}:${config.PROXY_PASSWORD}@${config.PROXY_IP}:${config.PROXY_PORT}`, {
      detectExternalIP: true,
      changeGeolocation: true,
      changeBrowserLanguage: true,
      changeTimezone: true,
      changeWebRTC: true,
    });
    log("Proxy settings applied", "green");
  }

  log("Launching browser...", "green");
  const browser = await plugin.launch({
    headless: false
  });
  const page = await browser.newPage();
  await page.setDefaultTimeout(3600000);

  // Enable request interception
  await page.setRequestInterception(true);

  // Monitor requests
  page.on('request', async request => {
    if (request.method() === 'POST' && request.url().includes('API/CreateAccount')) {
      try {
        const postData = request.postData();
        if (postData) {
          try {
            const parsedData = JSON.parse(postData);
            log(`CreateAccount Request Body:`, "blue");
            log(JSON.stringify(parsedData, null, 2), "blue");
          } catch {
            // If JSON parsing fails, log raw data
            log(`CreateAccount Request Body (raw):`, "blue");
            log(postData, "blue");
          }
        }
      } catch (err) {
        log(`Could not read post data: ${err.message}`, "red");
      }
    }
    request.continue();
  });

  // Remove or simplify response monitoring since we only want request body
  page.on('response', async response => {
    if (response.request().method() === 'POST' && response.url().includes('API/CreateAccount')) {
      log(`CreateAccount Response Status: ${response.status()}`, "purple");
    }
  });

  const viewport = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    height: document.documentElement.clientHeight,
  }));
  log(`Viewport: [Width: ${viewport.width} Height: ${viewport.height}]`, "green");

  // Check if the viewport is bigger than the current resolution.
  const { getCurrentResolution } = await import("win-screen-resolution");
  if (viewport.width > getCurrentResolution().width || viewport.height > getCurrentResolution().height) {
    log("Viewport is bigger than the current resolution, restarting...", "red");
    await delay(5000);
    await page.close();
    await browser.close();
    start();
  }

  await createAccount(page);
  await page.close();
  await browser.close();
  process.exit(0);

}

async function createAccount(page) {
  // Going to Outlook register page.
  await page.goto("https://outlook.live.com/owa/?nlp=1&signup=1");
  await page.waitForSelector('#usernameInput');

  // Generating Random Personal Info.
  const PersonalInfo = await generatePersonalInfo();
  await delay(1000);

  // Username
  await page.type('#usernameInput', PersonalInfo.username);
  await page.keyboard.press("Enter");

  // Password
  const password = await generatePassword();
  await page.waitForSelector('#Password');
  await page.type('#Password', password);
  await page.keyboard.press("Enter");

  // First Name and Last Name
  await page.waitForSelector('#firstNameInput');
  await page.type('#firstNameInput', PersonalInfo.randomFirstName);
  await page.type('#lastNameInput', PersonalInfo.randomLastName);
  await page.keyboard.press("Enter");

  // Birth Date.
  await page.waitForSelector('#BirthDay');
  await delay(1000);
  await page.select('#BirthDay', PersonalInfo.birthDay);
  await page.select('#BirthMonth', PersonalInfo.birthMonth);
  await page.type('#BirthYear', PersonalInfo.birthYear);
  await page.keyboard.press("Enter");
  const email = await page.$eval('#userDisplayName', el => el.textContent);
  log("Please solve the captcha", "yellow");

  // Waiting for confirmed account.
  await page.waitForSelector('#declineButton');
  log("Captcha Solved!", "green");
  await page.click('#declineButton');
  await page.waitForSelector('#mainApp');

  if (config.ADD_RECOVERY_EMAIL) {
    await page.goto("https://account.live.com/proofs/Manage");

    // First verify.
    await page.waitForSelector('#EmailAddress');
    const recoveryEmail = await recMail.getEmail();
    await page.type('#EmailAddress', recoveryEmail.email);
    await page.keyboard.press("Enter");
    await page.waitForSelector('#iOttText');
    log("Waiting for Email Code... (first verify)", "yellow");
    firstCode = await recMail.getMessage(recoveryEmail);
    log(`Email Code Received! Code: ${firstCode}`, "green");
    await page.type('#iOttText', firstCode);
    await page.keyboard.press("Enter");
    await page.waitForSelector('#idDiv_SAOTCS_Proofs_Section');

    // Second verify.
    await page.click('#idDiv_SAOTCS_Proofs_Section');
    await page.waitForSelector('#idTxtBx_SAOTCS_ProofConfirmation');
    await page.type('#idTxtBx_SAOTCS_ProofConfirmation', recoveryEmail.email);
    await page.keyboard.press("Enter");
    await page.waitForSelector('#idTxtBx_SAOTCC_OTC');
    log("Waiting for Email Code... (second verify)", "yellow");
    secondCode = await recMail.getMessage(recoveryEmail);
    log(`Email Code Received! Code: ${secondCode}`, "green");
    await page.type('#idTxtBx_SAOTCC_OTC', secondCode);
    await page.keyboard.press("Enter");
    await page.waitForSelector('#interruptContainer');
  }

  await writeCredentials(email, password);
}

async function writeCredentials(email, password) {
  // Writes account's credentials on "accounts.txt".
  const account = email + ":" + password;
  log(account, "green");
  fs.appendFile(config.ACCOUNTS_FILE, `\n${account}`, (err) => {
    if (err) {
      log(err, "red");
    }
  });
}

async function generatePersonalInfo() {
  const names = fs.readFileSync(config.NAMES_FILE, "utf8").split("\n");
  const randomFirstName = names[Math.floor(Math.random() * names.length)].trim();
  const randomLastName = names[Math.floor(Math.random() * names.length)].trim();
  const username = randomFirstName + randomLastName + Math.floor(Math.random() * 9999);
  const birthDay = (Math.floor(Math.random() * 28) + 1).toString()
  const birthMonth = (Math.floor(Math.random() * 12) + 1).toString()
  const birthYear = (Math.floor(Math.random() * 10) + 1990).toString()
  return { username, randomFirstName, randomLastName, birthDay, birthMonth, birthYear };
}

async function generatePassword() {
  const words = fs.readFileSync(config.WORDS_FILE, "utf8").split("\n");
  const firstword = words[Math.floor(Math.random() * words.length)].trim();
  const secondword = words[Math.floor(Math.random() * words.length)].trim();
  return firstword + secondword + Math.floor(Math.random() * 9999) + '!';
}

function delay(time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

start();