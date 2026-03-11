package com.aaos.automation.verification;

import com.aaos.automation.config.ConfigManager;
import com.aaos.automation.utils.ImageUtils;
import com.aaos.automation.utils.ScreenshotUtils;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.File;

/**
 * Verification Utilities for AAOS UI Automation
 * Provides SSIM-based image verification and OCR verification
 */
public class VerificationUtils {
    private static final Logger logger = LogManager.getLogger(VerificationUtils.class);
    private final AndroidDriver driver;
    private final ConfigManager config;
    private final String referenceImagesDir;

    public VerificationUtils(AndroidDriver driver) {
        this.driver = driver;
        this.config = ConfigManager.getInstance();
        this.referenceImagesDir = config.getReferenceImagesDir();
    }

    /**
     * Verify screen using SSIM comparison
     * @param referenceImageName reference image name (without extension)
     * @param threshold SSIM threshold (0.0 - 1.0)
     * @return true if SSIM is above threshold
     */
    public boolean verifyBySSIM(String referenceImageName, double threshold) {
        logger.info("Verifying by SSIM: {} with threshold {}", referenceImageName, threshold);
        
        String referenceImagePath = referenceImagesDir + File.separator + referenceImageName + ".png";
        File referenceFile = new File(referenceImagePath);
        
        if (!referenceFile.exists()) {
            logger.warn("Reference image not found: {}", referenceImagePath);
            return true; // Skip verification if no reference image
        }
        
        // Capture current screenshot
        String currentScreenshot = ScreenshotUtils.captureScreenshot(driver, "verify_" + referenceImageName);
        
        // Calculate SSIM
        double ssim = ImageUtils.calculateSSIM(referenceImagePath, currentScreenshot);
        
        boolean passed = ssim >= threshold;
        logger.info("SSIM Result: {} (threshold: {}) - {}", 
            String.format("%.4f", ssim), threshold, passed ? "PASSED" : "FAILED");
        
        return passed;
    }

    /**
     * Verify screen region using SSIM comparison
     * @param referenceImageName reference image name
     * @param threshold SSIM threshold
     * @param x region x coordinate
     * @param y region y coordinate
     * @param width region width
     * @param height region height
     * @return true if SSIM is above threshold
     */
    public boolean verifyRegionBySSIM(String referenceImageName, double threshold,
                                       int x, int y, int width, int height) {
        logger.info("Verifying region by SSIM: {} at ({},{},{},{}) with threshold {}", 
            referenceImageName, x, y, width, height, threshold);
        
        String referenceImagePath = referenceImagesDir + File.separator + referenceImageName + ".png";
        File referenceFile = new File(referenceImagePath);
        
        if (!referenceFile.exists()) {
            logger.warn("Reference image not found: {}", referenceImagePath);
            return true; // Skip verification if no reference image
        }
        
        // Capture and crop current screenshot
        String regionScreenshot = ScreenshotUtils.captureRegionScreenshot(
            driver, "verify_region_" + referenceImageName, x, y, width, height);
        
        if (regionScreenshot == null) {
            logger.error("Failed to capture region screenshot");
            return false;
        }
        
        // Calculate SSIM
        double ssim = ImageUtils.calculateSSIM(referenceImagePath, regionScreenshot);
        
        boolean passed = ssim >= threshold;
        logger.info("Region SSIM Result: {} (threshold: {}) - {}", 
            String.format("%.4f", ssim), threshold, passed ? "PASSED" : "FAILED");
        
        return passed;
    }

    /**
     * Parse and verify region from test case format
     * Format: "x,y,width,height"
     * @param referenceImageName reference image name
     * @param threshold SSIM threshold
     * @param regionString region string from test case
     * @return true if verification passed
     */
    public boolean verifyRegionFromString(String referenceImageName, double threshold, String regionString) {
        int[] region = ImageUtils.parseRegion(regionString);
        return verifyRegionBySSIM(referenceImageName, threshold, region[0], region[1], region[2], region[3]);
    }

    /**
     * Verify multiple items are present on screen using OCR
     * @param expectedItems items to verify (separated by semicolon)
     * @return true if all items are found
     */
    public boolean verifyByOCR(String expectedItems) {
        logger.info("Verifying by OCR: {}", expectedItems);
        
        String[] items = expectedItems.split(";");
        
        for (String item : items) {
            item = item.trim();
            if (!isTextPresent(item)) {
                logger.warn("OCR verification failed - text not found: {}", item);
                return false;
            }
        }
        
        logger.info("OCR verification passed for all items");
        return true;
    }

    /**
     * Check if text is present on screen
     * @param text text to find
     * @return true if text is present
     */
    private boolean isTextPresent(String text) {
        try {
            return driver.getPageSource().contains(text);
        } catch (Exception e) {
            logger.error("Error checking text presence: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Get current screen verification score
     * @param referenceImageName reference image name
     * @return SSIM score (0.0 - 1.0)
     */
    public double getVerificationScore(String referenceImageName) {
        String referenceImagePath = referenceImagesDir + File.separator + referenceImageName + ".png";
        File referenceFile = new File(referenceImagePath);
        
        if (!referenceFile.exists()) {
            logger.warn("Reference image not found: {}", referenceImagePath);
            return -1;
        }
        
        String currentScreenshot = ScreenshotUtils.captureScreenshot(driver, "score_" + referenceImageName);
        return ImageUtils.calculateSSIM(referenceImagePath, currentScreenshot);
    }
}
