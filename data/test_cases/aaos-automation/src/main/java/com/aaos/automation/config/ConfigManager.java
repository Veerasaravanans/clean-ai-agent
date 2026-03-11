package com.aaos.automation.config;

import lombok.Getter;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

/**
 * Configuration manager for AAOS UI Automation
 * Loads and provides access to configuration properties
 */
@Getter
public class ConfigManager {
    private static final Logger logger = LogManager.getLogger(ConfigManager.class);
    private static ConfigManager instance;
    private final Properties properties;

    // Device Configuration
    private String deviceName;
    private String platformName;
    private String platformVersion;
    private String automationName;
    private String deviceUdid;

    // Appium Configuration
    private String appiumServerUrl;
    private int appiumServerTimeout;

    // Display Configuration
    private int displayWidth;
    private int displayHeight;

    // Test Configuration
    private int implicitWait;
    private int explicitWait;
    private int retryCount;

    // Screenshot Configuration
    private String screenshotDir;
    private boolean screenshotOnFailure;

    // Verification Configuration
    private double defaultSsimThreshold;
    private String referenceImagesDir;

    // Report Configuration
    private String reportDir;
    private String reportName;

    private ConfigManager() {
        properties = new Properties();
        loadProperties();
        initializeConfig();
    }

    public static synchronized ConfigManager getInstance() {
        if (instance == null) {
            instance = new ConfigManager();
        }
        return instance;
    }

    private void loadProperties() {
        try {
            // Try loading from classpath
            var inputStream = getClass().getClassLoader().getResourceAsStream("config.properties");
            if (inputStream != null) {
                properties.load(inputStream);
                logger.info("Configuration loaded from classpath");
            } else {
                // Fallback to file system
                properties.load(new FileInputStream("src/main/resources/config.properties"));
                logger.info("Configuration loaded from file system");
            }
        } catch (IOException e) {
            logger.error("Failed to load configuration: {}", e.getMessage());
            throw new RuntimeException("Configuration load failed", e);
        }
    }

    private void initializeConfig() {
        // Device Configuration
        deviceName = getProperty("device.name", "AAOS_Emulator");
        platformName = getProperty("device.platform.name", "Android");
        platformVersion = getProperty("device.platform.version", "13");
        automationName = getProperty("device.automation.name", "UiAutomator2");
        deviceUdid = getProperty("device.udid", "emulator-5554");

        // Appium Configuration
        appiumServerUrl = getProperty("appium.server.url", "http://127.0.0.1:4723");
        appiumServerTimeout = Integer.parseInt(getProperty("appium.server.timeout", "60"));

        // Display Configuration
        displayWidth = Integer.parseInt(getProperty("display.width", "1408"));
        displayHeight = Integer.parseInt(getProperty("display.height", "792"));

        // Test Configuration
        implicitWait = Integer.parseInt(getProperty("test.implicit.wait", "10"));
        explicitWait = Integer.parseInt(getProperty("test.explicit.wait", "30"));
        retryCount = Integer.parseInt(getProperty("test.retry.count", "3"));

        // Screenshot Configuration
        screenshotDir = getProperty("screenshot.dir", "./screenshots");
        screenshotOnFailure = Boolean.parseBoolean(getProperty("screenshot.on.failure", "true"));

        // Verification Configuration
        defaultSsimThreshold = Double.parseDouble(getProperty("verification.ssim.default.threshold", "0.85"));
        referenceImagesDir = getProperty("verification.reference.images.dir", "./reference_images");

        // Report Configuration
        reportDir = getProperty("report.dir", "./reports");
        reportName = getProperty("report.name", "AAOS_UI_Test_Report");

        logger.info("Configuration initialized successfully");
    }

    private String getProperty(String key, String defaultValue) {
        return properties.getProperty(key, defaultValue);
    }

    public String getProperty(String key) {
        return properties.getProperty(key);
    }
}
