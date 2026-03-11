package com.aaos.automation.listeners;

import com.aaos.automation.driver.DriverManager;
import com.aaos.automation.reporting.ExtentReportManager;
import com.aaos.automation.utils.ScreenshotUtils;
import com.aventstack.extentreports.Status;
import io.appium.java_client.android.AndroidDriver;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

/**
 * TestNG Listener for AAOS UI Automation
 * Handles test lifecycle events and reporting
 */
public class TestListener implements ITestListener {
    private static final Logger logger = LogManager.getLogger(TestListener.class);

    @Override
    public void onStart(ITestContext context) {
        logger.info("Test Suite Started: {}", context.getName());
    }

    @Override
    public void onFinish(ITestContext context) {
        logger.info("Test Suite Finished: {}", context.getName());
        logger.info("Passed: {}, Failed: {}, Skipped: {}", 
            context.getPassedTests().size(),
            context.getFailedTests().size(), 
            context.getSkippedTests().size());
    }

    @Override
    public void onTestStart(ITestResult result) {
        logger.info("Starting Test: {}", result.getMethod().getMethodName());
    }

    @Override
    public void onTestSuccess(ITestResult result) {
        logger.info("Test PASSED: {}", result.getMethod().getMethodName());
    }

    @Override
    public void onTestFailure(ITestResult result) {
        logger.error("Test FAILED: {}", result.getMethod().getMethodName());
        logger.error("Failure Reason: {}", result.getThrowable().getMessage());
        
        // Capture screenshot on failure
        try {
            if (DriverManager.isDriverActive()) {
                AndroidDriver driver = DriverManager.getDriver();
                String screenshotPath = ScreenshotUtils.captureScreenshot(driver, 
                    result.getMethod().getMethodName() + "_FAILURE");
                
                // Add screenshot to report
                if (ExtentReportManager.getTest() != null && screenshotPath != null) {
                    ExtentReportManager.getTest().log(Status.FAIL, 
                        "Screenshot captured on failure")
                        .addScreenCaptureFromPath(screenshotPath);
                }
            }
        } catch (Exception e) {
            logger.error("Failed to capture failure screenshot: {}", e.getMessage());
        }
    }

    @Override
    public void onTestSkipped(ITestResult result) {
        logger.warn("Test SKIPPED: {}", result.getMethod().getMethodName());
        if (result.getThrowable() != null) {
            logger.warn("Skip Reason: {}", result.getThrowable().getMessage());
        }
    }

    @Override
    public void onTestFailedButWithinSuccessPercentage(ITestResult result) {
        logger.warn("Test Failed but within success percentage: {}", 
            result.getMethod().getMethodName());
    }
}
