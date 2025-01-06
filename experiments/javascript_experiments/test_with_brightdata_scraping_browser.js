const puppeteer = require('puppeteer-core');
const fs = require("fs");
const config = require('../microsoft-account-creator/src/config');
const colors = require("colors");
require('dotenv').config();

function log(message, color) {
  const timestamp = new Date().toLocaleTimeString();
  console.log(`${colors[color](`[${timestamp}]`,)} ${message}`);
}
const axios = require('axios');

async function start() {
  console.clear();

  log("Starting...", "green");

  const BROWSER_WS = process.env.TBROWSER_WS;
  
  if (!BROWSER_WS) {
    log("Error: TBROWSER_WS environment variable is not set", "red");
    process.exit(1);
  }
  
  try {
    log("Connecting to Bright Data Scraping Browser...", "yellow");
    const browser = await puppeteer.connect({
      browserWSEndpoint: BROWSER_WS,
    });
    
    const page = await browser.newPage();

    // Setup CDP session for CAPTCHA handling
    const client = await page.createCDPSession();

    await createAccount(page, client);
    await page.close();
    await browser.close();
    process.exit(0);
    
  } catch (error) {
    log(`Error: ${error.message}`, "red");
    process.exit(1);
  }
}

async function takeScreenshot(page, name) {
  const screenshotsDir = './screenshots';
  if (!fs.existsSync(screenshotsDir)){
    fs.mkdirSync(screenshotsDir);
  }
  await page.screenshot({ 
    path: `${screenshotsDir}/${Date.now()}_${name}.png`,
    fullPage: true 
  });
  log(`Screenshot saved: ${name}`, "blue");
  await delay(2000); // 5 second delay after each screenshot
}

async function createAccount(page, client) {
  // Add variable to store the arkose blob
  let arkoseBlob = null;

  // Setup network monitoring with CDP
  await client.send('Network.enable');
  
  client.on('Network.requestWillBeSent', request => {
    if (request.request.url.includes('API/CreateAccount')) {
      log(`Request: ${request.request.method} ${request.request.url}`, "cyan");
      if (request.request.postData) {
        log(`Request data: ${request.request.postData}`, "yellow");
      }
    }
  });

  client.on('Network.responseReceived', async response => {
    if (response.response.url.includes('API/CreateAccount')) {
      log(`Response: ${response.response.status} ${response.response.url}`, 
          response.response.status < 400 ? "cyan" : "red");
      
      try {
        const responseBody = await client.send('Network.getResponseBody', {
          requestId: response.requestId
        });
        
        try {
          const bodyJson = JSON.parse(responseBody.body);
          if (bodyJson.error && bodyJson.error.data) {
            log(`Raw Error data: ${JSON.stringify(bodyJson.error.data, null, 2)}`, "red");
            
            const errorData = JSON.parse(bodyJson.error.data);
            const cleanedError = {
              risk_assessment_details: errorData.riskAssessmentDetails,
              rep_map_request_identifier_details: errorData.repMapRequestIdentifierDetails,
              dfp_request_id: errorData.dfpRequestId,
              arkose_blob: errorData.arkoseBlob
            };
            
            log(`Cleaned Error Data: ${JSON.stringify(cleanedError, null, 2)}`, "yellow");

            // Store the arkose blob for later use
            arkoseBlob = cleanedError.arkose_blob;
          }
        } catch (parseError) {
          // Not JSON or can't be parsed, ignore
        }
      } catch (bodyError) {
        // Can't get response body, ignore
      }
      
      log(`Response headers: ${JSON.stringify(response.response.headers)}`, "yellow");
    }
  });

  // Going to Outlook register page.
  await page.goto("https://signup.live.com/signup?lcid=1033");
  await takeScreenshot(page, "initial_page");

  // Generating Random Personal Info.
  const PersonalInfo = await generatePersonalInfo();

  // Username
  await page.type('#usernameInput', PersonalInfo.username+'@outlook.com');
  await page.keyboard.press("Enter");
  await takeScreenshot(page, "after_username");

  // Password
  const password = await generatePassword();
  const passwordSelector = '#pageContent > div > form > div.___102hf4m.f1tyq0we.f11qmguv.f1wv5yrl > div > div:nth-child(1) > div > div > input';
  await page.waitForSelector(passwordSelector);
  
  // Remove id and type attributes to avoid detection
  await page.evaluate((selector) => {
    const element = document.querySelector(selector);
    element.removeAttribute('id');
    element.removeAttribute('type');
  }, passwordSelector);
  
  await page.type(passwordSelector, password);
  await page.keyboard.press("Enter");
  await takeScreenshot(page, "after_password");

  // First Name and Last Name
  await page.waitForSelector('#firstNameInput');
  await page.type('#firstNameInput', PersonalInfo.randomFirstName);
  await page.type('#lastNameInput', PersonalInfo.randomLastName);
  await page.keyboard.press("Enter");
  await takeScreenshot(page, "after_name");

  // Birth Date.
  await page.waitForSelector('#BirthDay');
  await delay(1000);
  await page.select('#BirthDay', PersonalInfo.birthDay);
  await page.select('#BirthMonth', PersonalInfo.birthMonth);
  await page.type('#BirthYear', PersonalInfo.birthYear);
  await page.keyboard.press("Enter");
  await takeScreenshot(page, "after_birthdate");

  const email = await page.$eval('#userDisplayName', el => el.textContent);
  log("Please solve the captcha", "yellow");
  await takeScreenshot(page, "before_captcha");
  await delay(5000); // Wait 5 seconds before attempting solve

  // Click on body to ensure no focus, then use keyboard navigation
  await page.click('body');
  await delay(1000);
  await page.keyboard.press('Tab');
  await delay(500);
  await page.keyboard.press('Tab');
  await delay(500);
  await page.keyboard.press('Enter');
  log("Navigated to captcha using keyboard", "yellow");
  await takeScreenshot(page, "after_captcha_navigation");

  // Try to solve captcha using Bright Data first
  try {
    log('Waiting for Bright Data to solve captcha...', 'yellow');
    await delay(5000); // Wait 5 seconds before attempting solve
    await takeScreenshot(page, "after_after_captcha_navigation");

    const { status } = await client.send('Captcha.waitForSolve', {
      detectTimeout: 30000, // 30 seconds timeout
    });
    log(`Bright Data Captcha solve status: ${status}`, 'green');
    
    if (status !== 'solved') {
      // If Bright Data fails, try 2captcha as fallback if we have arkose blob
      if (arkoseBlob) {
        log('Bright Data solve failed, attempting 2captcha...', 'yellow');
        try {
          const token = await solveArkoseCaptcha(arkoseBlob);
          log(`Got captcha token from 2captcha: ${token}`, 'green');
          // TODO: Implement using the token
        } catch (error) {
          log(`Failed to solve captcha with 2captcha: ${error.message}`, 'red');
        }
      }
    }
  } catch (error) {
    log(`Error with Bright Data captcha solving: ${error.message}`, 'red');
    // Try 2captcha as fallback
    if (arkoseBlob) {
      log('Attempting 2captcha as fallback...', 'yellow');
      try {
        const token = await solveArkoseCaptcha(arkoseBlob);
        log(`Got captcha token from 2captcha: ${token}`, 'green');
        // TODO: Implement using the token
      } catch (error) {
        log(`Failed to solve captcha with 2captcha: ${error.message}`, 'red');
      }
    }
  }

  await takeScreenshot(page, "after_captcha");
  await writeCredentials(email, password);
  await takeScreenshot(page, "final_page");
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

async function solveArkoseCaptcha(arkoseBlob) {
  try {
    log('Initiating 2captcha solve request for Arkose Labs...', 'yellow');
    log(`Using arkose blob: ${arkoseBlob}`, 'cyan');
    
    const taskData = {
      clientKey: process.env.TWOCAPTCHA_API_KEY,
      task: {
        type: "FunCaptchaTaskProxyless",
        websiteURL: "https://signup.live.com/",
        websitePublicKey: "B7D8911C-5CC8-A9A3-35B0-554ACEE604DA",
        funcaptchaApiJSSubdomain: "iframe.arkoselabs.com",
        data: JSON.stringify({ blob: arkoseBlob }),
        userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
      }
    };

    const createTaskResponse = await axios.post('https://api.2captcha.com/createTask', taskData);
    log(`Create task response: ${JSON.stringify(createTaskResponse.data)}`, 'cyan');

    if (createTaskResponse.data.errorId !== 0) {
      throw new Error(`Failed to create captcha task: ${createTaskResponse.data.errorDescription}`);
    }

    const taskId = createTaskResponse.data.taskId;
    log(`Got task ID: ${taskId}`, 'green');

    // Poll for the result
    let attempts = 0;
    const maxAttempts = 60;

    while (attempts < maxAttempts) {
      await delay(5000); // Wait 10 seconds between checks

      const resultResponse = await axios.post('https://api.2captcha.com/getTaskResult', {
        clientKey: process.env.TWOCAPTCHA_API_KEY,
        taskId: taskId
      });

      if (resultResponse.data.status === 'ready') {
        log('Captcha solution found!', 'green');
        return resultResponse.data.solution.token;
      }

      attempts++;
      log(`Waiting for solution... Attempt ${attempts}/${maxAttempts}`, 'yellow');
    }

    throw new Error('Timeout waiting for captcha solution');
  } catch (error) {
    log(`Error in solveArkoseCaptcha: ${error.message}`, 'red');
    throw error;
  }
}

start();
