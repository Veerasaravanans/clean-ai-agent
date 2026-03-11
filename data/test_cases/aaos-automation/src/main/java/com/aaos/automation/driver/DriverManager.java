package com.aaos.automation.driver;

import com.aaos.automation.config.ConfigManager;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.net.MalformedURLException;
import java.net.URL;
import java.time.Duration;

/**
 * Driver Manager for AAOS Android Automotive Testing
 * Manages AndroidDriver lifecycle for UI automation
 */
public class DriverManager {
    private static final Logger logger = LogManager.getLogger(DriverManager.class);
    private static final ThreadLocal<AndroidDriver> driverThreadLocal = new ThreadLocal<>();
    private static final ConfigManager config = ConfigManager.getInstance();

    private DriverManager() {
        // Private constructor to prevent instantiation
    }

    /**
     * Initialize and get AndroidDriver instance
     * @return AndroidDriver instance
     */
    public static AndroidDriver getDriver() {
        if (driverThreadLocal.get() == null) {
            initializeDriver();
        }
        return driverThreadLocal.get();
    }

    /**
     * Initialize AndroidDriver with AAOS configuration
     */
    public static void initializeDriver() {
        logger.info("Initializing AndroidDriver for AAOS...");

        UiAutomator2Options options = new UiAutomator2Options();
        
        // Device capabilities
        options.setDeviceName(config.getDeviceName());
        options.setPlatformName(config.getPlatformName());
        options.setPlatformVersion(config.getPlatformVersion());
        options.setAutomationName(config.getAutomationName());
        options.setUdid(config.getDeviceUdid());
        
        // AAOS specific capabilities
        options.setCapability("appium:autoGrantPermissions", true);
        options.setCapability("appium:noReset", true);
        options.setCapability("appium:fullReset", false);
        options.setCapability("appium:newCommandTimeout", 300);
        options.setCapability("appium:skipDeviceInitialization", false);
        options.setCapability("appium:skipServerInstallation", false);
        
        // Enable UiAutomator2 for large displays
        options.setCapability("appium:disableWindowAnimation", true);
        options.setCapability("appium:skipUnlock", true);

        try {
            URL appiumServerUrl = new URL(config.getAppiumServerUrl());
            AndroidDriver driver = new AndroidDriver(appiumServerUrl, options);
            
            // Set implicit wait
            driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(config.getImplicitWait()));
            
            driverThreadLocal.set(driver);
            logger.info("AndroidDriver initialized successfully");
            
        } catch (MalformedURLException e) {
            logger.error("Invalid Appium server URL: {}", e.getMessage());
            throw new RuntimeException("Failed to initialize driver", e);
        }
    }

    /**
     * Quit and cleanup driver instance
     */
    public static void quitDriver() {
        AndroidDriver driver = driverThreadLocal.get();
        if (driver != null) {
            logger.info("Quitting AndroidDriver...");
            driver.quit();
            driverThreadLocal.remove();
            logger.info("AndroidDriver quit successfully");
        }
    }

    /**
     * Check if driver is active
     * @return true if driver is active
     */
    public static boolean isDriverActive() {
        return driverThreadLocal.get() != null;
    }

    /**
     * Reset the current app state
     */
    public static void resetApp() {
        AndroidDriver driver = getDriver();
        if (driver != null) {
            logger.info("Resetting app state...");
            driver.terminateApp(driver.getCurrentPackage());
            driver.activateApp(driver.getCurrentPackage());
        }
    }

    /**
     * Navigate to home screen
     */
    public static void goToHome() {
        AndroidDriver driver = getDriver();
        if (driver != null) {
            logger.info("Navigating to home screen...");
            driver.pressKey(new io.appium.java_client.android.nativekey.KeyEvent(
                io.appium.java_client.android.nativekey.AndroidKey.HOME));
        }
    }

    /**
     * Press back button
     */
    public static void pressBack() {
        AndroidDriver driver = getDriver();
        if (driver != null) {
            logger.info("Pressing back button...");
            driver.pressKey(new io.appium.java_client.android.nativekey.KeyEvent(
                io.appium.java_client.android.nativekey.AndroidKey.BACK));
        }
    }
}
