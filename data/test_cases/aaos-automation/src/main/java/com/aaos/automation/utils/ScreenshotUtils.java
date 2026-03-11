package com.aaos.automation.utils;

import com.aaos.automation.config.ConfigManager;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.openqa.selenium.OutputType;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Screenshot Utilities for AAOS UI Automation
 */
public class ScreenshotUtils {
    private static final Logger logger = LogManager.getLogger(ScreenshotUtils.class);
    private static final String SCREENSHOT_DIR;

    static {
        SCREENSHOT_DIR = ConfigManager.getInstance().getScreenshotDir();
        createDirectoryIfNotExists(SCREENSHOT_DIR);
    }

    /**
     * Capture screenshot and save to file
     * @param driver AndroidDriver instance
     * @param screenshotName name for the screenshot
     * @return path to the screenshot file
     */
    public static String captureScreenshot(AndroidDriver driver, String screenshotName) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String fileName = String.format("%s_%s.png", screenshotName, timestamp);
        String filePath = SCREENSHOT_DIR + File.separator + fileName;

        try {
            File screenshot = driver.getScreenshotAs(OutputType.FILE);
            Files.copy(screenshot.toPath(), Paths.get(filePath));
            logger.info("Screenshot captured: {}", filePath);
            return filePath;
        } catch (IOException e) {
            logger.error("Failed to capture screenshot: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Capture screenshot as byte array
     * @param driver AndroidDriver instance
     * @return screenshot as byte array
     */
    public static byte[] captureScreenshotAsBytes(AndroidDriver driver) {
        return driver.getScreenshotAs(OutputType.BYTES);
    }

    /**
     * Capture screenshot for region
     * @param driver AndroidDriver instance
     * @param screenshotName screenshot name
     * @param x region x coordinate
     * @param y region y coordinate
     * @param width region width
     * @param height region height
     * @return path to cropped screenshot
     */
    public static String captureRegionScreenshot(AndroidDriver driver, String screenshotName,
                                                  int x, int y, int width, int height) {
        String fullScreenshot = captureScreenshot(driver, screenshotName + "_full");
        if (fullScreenshot == null) {
            return null;
        }

        try {
            // Use ImageUtils to crop the region
            String croppedPath = SCREENSHOT_DIR + File.separator + screenshotName + "_cropped.png";
            ImageUtils.cropImage(fullScreenshot, croppedPath, x, y, width, height);
            return croppedPath;
        } catch (Exception e) {
            logger.error("Failed to crop screenshot region: {}", e.getMessage());
            return fullScreenshot;
        }
    }

    /**
     * Create directory if it doesn't exist
     * @param dirPath directory path
     */
    private static void createDirectoryIfNotExists(String dirPath) {
        Path path = Paths.get(dirPath);
        if (!Files.exists(path)) {
            try {
                Files.createDirectories(path);
                logger.info("Created directory: {}", dirPath);
            } catch (IOException e) {
                logger.error("Failed to create directory: {}", e.getMessage());
            }
        }
    }
}
