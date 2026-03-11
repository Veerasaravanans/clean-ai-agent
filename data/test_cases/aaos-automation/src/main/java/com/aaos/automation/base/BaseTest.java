package com.aaos.automation.base;

import com.aaos.automation.config.ConfigManager;
import com.aaos.automation.driver.DriverManager;
import com.aaos.automation.reporting.ExtentReportManager;
import com.aaos.automation.utils.ScreenshotUtils;
import com.aventstack.extentreports.ExtentTest;
import com.aventstack.extentreports.Status;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.testng.ITestResult;
import org.testng.annotations.*;

/**
 * Base Test Class for AAOS UI Automation
 * Provides common test lifecycle management and utilities
 */
public abstract class BaseTest {
    protected static final Logger logger = LogManager.getLogger(BaseTest.class);
    protected AndroidDriver driver;
    protected ConfigManager config;
    protected ExtentTest extentTest;

    @BeforeSuite(alwaysRun = true)
    public void beforeSuite() {
        logger.info("========== AAOS UI Automation Suite Started ==========");
        ExtentReportManager.initializeReport();
    }

    @BeforeClass(alwaysRun = true)
    public void beforeClass() {
        logger.info("Setting up test class: {}", this.getClass().getSimpleName());
        config = ConfigManager.getInstance();
    }

    @BeforeMethod(alwaysRun = true)
    public void beforeMethod(ITestResult result) {
        logger.info("Starting test: {}", result.getMethod().getMethodName());
        
        // Initialize driver if not already done
        driver = DriverManager.getDriver();
        
        // Create extent test entry
        extentTest = ExtentReportManager.createTest(
            result.getMethod().getMethodName(),
            result.getMethod().getDescription()
        );
        
        // Navigate to home to ensure clean state
        DriverManager.goToHome();
        sleep(1000);
    }

    @AfterMethod(alwaysRun = true)
    public void afterMethod(ITestResult result) {
        String testName = result.getMethod().getMethodName();
        
        switch (result.getStatus()) {
            case ITestResult.SUCCESS:
                logger.info("Test PASSED: {}", testName);
                extentTest.log(Status.PASS, "Test passed successfully");
                break;
                
            case ITestResult.FAILURE:
                logger.error("Test FAILED: {}", testName);
                extentTest.log(Status.FAIL, "Test failed: " + result.getThrowable().getMessage());
                
                // Capture screenshot on failure
                if (config.isScreenshotOnFailure()) {
                    String screenshotPath = ScreenshotUtils.captureScreenshot(driver, testName);
                    extentTest.addScreenCaptureFromPath(screenshotPath);
                }
                break;
                
            case ITestResult.SKIP:
                logger.warn("Test SKIPPED: {}", testName);
                extentTest.log(Status.SKIP, "Test skipped: " + 
                    (result.getThrowable() != null ? result.getThrowable().getMessage() : "Unknown reason"));
                break;
        }
    }

    @AfterClass(alwaysRun = true)
    public void afterClass() {
        logger.info("Cleaning up test class: {}", this.getClass().getSimpleName());
    }

    @AfterSuite(alwaysRun = true)
    public void afterSuite() {
        logger.info("Tearing down test suite...");
        DriverManager.quitDriver();
        ExtentReportManager.flushReport();
        logger.info("========== AAOS UI Automation Suite Completed ==========");
    }

    /**
     * Sleep for specified milliseconds
     * @param millis milliseconds to sleep
     */
    protected void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            logger.warn("Sleep interrupted");
        }
    }

    /**
     * Log step information to extent report
     * @param stepNumber step number
     * @param description step description
     */
    protected void logStep(int stepNumber, String description) {
        String message = String.format("Step %d: %s", stepNumber, description);
        logger.info(message);
        extentTest.log(Status.INFO, message);
    }

    /**
     * Log verification result
     * @param success whether verification passed
     * @param message verification message
     */
    protected void logVerification(boolean success, String message) {
        if (success) {
            logger.info("VERIFICATION PASSED: {}", message);
            extentTest.log(Status.PASS, "Verification: " + message);
        } else {
            logger.error("VERIFICATION FAILED: {}", message);
            extentTest.log(Status.FAIL, "Verification: " + message);
        }
    }

    /**
     * Capture screenshot and add to report
     * @param screenshotName name for the screenshot
     */
    protected void captureScreenshot(String screenshotName) {
        String screenshotPath = ScreenshotUtils.captureScreenshot(driver, screenshotName);
        extentTest.addScreenCaptureFromPath(screenshotPath);
    }
}
