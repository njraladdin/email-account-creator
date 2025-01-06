const puppeteerExtra = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const axios = require('axios');
const os = require('os');
const fs = require('fs').promises;
const path = require('path');

const dotenv = require('dotenv');
dotenv.config();
const TWOCAPTCHA_API_KEY = process.env.TWOCAPTCHA_API_KEY;

const ENABLE_PROXY = false; // Set to true to enable proxy, false to disable

const BROWSER_CLEANUP_DELAY = 400; // ms to wait after browser closes

// Setup puppeteer with stealth plugin
puppeteerExtra.use(StealthPlugin());


// ResultTracker class (keeping this as a class 


async function launchBrowser(proxyConfig = null, headless = true, activeUserAgents) {
    const randomProfile = Math.floor(Math.random() * 4) + 1;

    try {
        const browser = await puppeteerExtra.launch({
            headless: headless,
            // executablePath:  os.platform().startsWith('win') 
            // ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" 
            // : "/usr/bin/google-chrome",
            userDataDir: 'chrome-user-data',
            protocolTimeout: 30000,
            args: [
                '--no-sandbox',
                '--disable-gpu',
                '--enable-webgl',
                '--window-size=1920,1080',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-first-run',
                '--no-default-browser-check',
                '--password-store=basic',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--lang=en',
                '--disable-web-security',
                '--flag-switches-begin --disable-site-isolation-trials --flag-switches-end',
                `--profile-directory=Profile ${randomProfile}`,
                proxyConfig ? `--proxy-server=${proxyConfig.host}:${proxyConfig.port}` : ''
            ].filter(Boolean),
            ignoreDefaultArgs: ['--enable-automation', '--enable-blink-features=AutomationControlled'],
            defaultViewport: null,
        });

        // Update page configuration
        browser.on('targetcreated', async (target) => {
            const page = await target.page();
            if (page) {
                await page.evaluateOnNewDocument(() => {
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    delete navigator.__proto__.webdriver;
                });
                
                const randomUserAgent = activeUserAgents[Math.floor(Math.random() * activeUserAgents.length)];
                await page.setUserAgent(randomUserAgent);
                
                await page.setDefaultTimeout(30000);
                await page.setDefaultNavigationTimeout(30000);

                if (proxyConfig?.username && proxyConfig?.password) {
                    await page.authenticate({
                        username: proxyConfig.username,
                        password: proxyConfig.password
                    });
                }
            }
        });

        // Add cleanup function
        browser.cleanup = async () => {
            try {
                await browser.close();
            } catch (error) {
                console.error(`Error closing browser: ${error.message}`);
            }
            await new Promise(resolve => setTimeout(resolve, BROWSER_CLEANUP_DELAY));
        };

        return browser;
    } catch (error) {
        throw error;
    }
}

async function solve2Captcha(sitekey, pageUrl, apiKey, userAgent) {
    try {
        console.log('Initiating 2captcha solve request...');

        const taskData = {
            clientKey: apiKey,
            task: {
                type: "RecaptchaV2TaskProxyless",
                websiteURL: pageUrl,
                websiteKey: sitekey,
                userAgent: userAgent,
                isInvisible: false
            }
        };

        const createTaskResponse = await axios.post('https://api.2captcha.com/createTask', taskData);
        console.log('Create task response:', createTaskResponse.data);

        if (createTaskResponse.data.errorId !== 0) {
            throw new Error(`Failed to create captcha task: ${createTaskResponse.data.errorDescription}`);
        }

        const taskId = createTaskResponse.data.taskId;
        console.log('Got task ID:', taskId);

        // Poll for the result
        let attempts = 0;
        const maxAttempts = 60;

        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 10000));

            const resultResponse = await axios.post('https://api.2captcha.com/getTaskResult', {
                clientKey: apiKey,
                taskId: taskId
            });

            if (resultResponse.data.status === 'ready') {
                console.log('Solution found!');
                return resultResponse.data.solution.token;
            }

            attempts++;
        }

        throw new Error('Timeout waiting for captcha solution');
    } catch (error) {
        console.error('Error in solve2Captcha:', error);
        throw error;
    }
}

async function generatePersonalInfo() {
    // Function to generate random string
    const generateName = (length) => {
        const consonants = 'bcdfghjklmnpqrstvwxyz';
        const vowels = 'aeiou';
        let name = '';
        for (let i = 0; i < length; i++) {
            name += (i % 2 === 0) 
                ? consonants[Math.floor(Math.random() * consonants.length)] 
                : vowels[Math.floor(Math.random() * vowels.length)];
        }
        return name.charAt(0).toUpperCase() + name.slice(1);
    };

    const randomFirstName = generateName(5 + Math.floor(Math.random() * 3));
    const randomLastName = generateName(5 + Math.floor(Math.random() * 3));
    const username = randomFirstName.toLowerCase() + randomLastName.toLowerCase() + Math.floor(Math.random() * 9999);
    const birthDay = (Math.floor(Math.random() * 28) + 1).toString();
    const birthMonth = (Math.floor(Math.random() * 12) + 1).toString();
    const birthYear = (Math.floor(Math.random() * 10) + 1990).toString();
    return { username, randomFirstName, randomLastName, birthDay, birthMonth, birthYear };
}

async function generatePassword() {
    const generateWord = (length) => {
        const consonants = 'bcdfghjklmnpqrstvwxyz';
        const vowels = 'aeiou';
        let word = '';
        for (let i = 0; i < length; i++) {
            word += (i % 2 === 0) 
                ? consonants[Math.floor(Math.random() * consonants.length)] 
                : vowels[Math.floor(Math.random() * vowels.length)];
        }
        return word;
    };

    const firstword = generateWord(5 + Math.floor(Math.random() * 3));
    const secondword = generateWord(5 + Math.floor(Math.random() * 3));
    return firstword + secondword + Math.floor(Math.random() * 9999) + '!';
}

async function main() {
    const activeUserAgents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ];

    const proxyConfig = ENABLE_PROXY ? {
        host: process.env.PROXY_HOST,
        port: process.env.PROXY_PORT,
        username: process.env.PROXY_USERNAME,
        password: process.env.PROXY_PASSWORD
    } : null;

    let browser;
    try {
        console.log(`Launching browser... ${ENABLE_PROXY ? 'with proxy' : 'without proxy'}`);
        browser = await launchBrowser(proxyConfig, false, activeUserAgents);
        
        const page = await browser.newPage();
        console.log('Navigating to Outlook signup...');
        await page.goto('https://outlook.live.com/owa/?nlp=1&signup=1', {
            waitUntil: 'networkidle0',
            timeout: 60000
        });

        // Wait for username input and fill in
        console.log('Starting signup process...');
        const personalInfo = await generatePersonalInfo();
        await page.waitForSelector('#usernameInput');
        await page.type('#usernameInput', personalInfo.username);
        await page.keyboard.press('Enter');

        // Wait for and fill password
        const password = await generatePassword();
        await page.waitForSelector('#Password');
        await page.type('#Password', password);
        await page.keyboard.press('Enter');

        // Fill in name fields
        await page.waitForSelector('#firstNameInput');
        await page.type('#firstNameInput', personalInfo.randomFirstName);
        await page.type('#lastNameInput', personalInfo.randomLastName);
        await page.keyboard.press('Enter');

        // Fill in birth date
        await page.waitForSelector('#BirthDay');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Small delay before selecting
        await page.select('#BirthDay', personalInfo.birthDay);
        await page.select('#BirthMonth', personalInfo.birthMonth);
        await page.type('#BirthYear', personalInfo.birthYear);
        await page.keyboard.press('Enter');

        // Get the email address
        const email = await page.$eval('#userDisplayName', el => el.textContent);
        console.log('Created account:', email);

        // Save account details
        const accountInfo = {
            email,
            password,
            firstName: personalInfo.randomFirstName,
            lastName: personalInfo.randomLastName,
            dateCreated: new Date().toISOString()
        };
        

        // Keep browser open briefly to verify
        await new Promise(resolve => setTimeout(resolve, 3000000));

    } catch (error) {
        console.error('Error in main:', error);
    } finally {
        if (browser) {
            console.log('Cleaning up browser...');
            await browser.cleanup();
        }
    }
}

// Add this at the bottom of the file to run the main function
if (require.main === module) {
    main().catch(console.error);
}